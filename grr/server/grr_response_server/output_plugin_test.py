#!/usr/bin/env python
"""Tests for grr.lib.output_plugin."""
from __future__ import absolute_import
from __future__ import unicode_literals


from future.utils import itervalues

from grr_response_core.lib import flags
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_server import aff4
from grr_response_server import output_plugin
from grr_response_server.flows.general import transfer
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import test_lib


class TestOutputPluginWithArgs(output_plugin.OutputPlugin):

  args_type = rdf_flow_runner.FlowRunnerArgs

  def ProcessResponses(self, responses):
    pass


class OutputPluginTest(test_lib.GRRBaseTest):

  def testGetPluginArgsHandlesMissingPluginsCorrectly(self):
    descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="TestOutputPluginWithArgs",
        plugin_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__))
    serialized = descriptor.SerializeToString()

    deserialized = rdf_output_plugin.OutputPluginDescriptor()
    deserialized.ParseFromString(serialized)
    self.assertEqual(deserialized, descriptor)
    self.assertEqual(deserialized.GetPluginClass(), TestOutputPluginWithArgs)

    opr = registry.OutputPluginRegistry
    with utils.Stubber(opr, "PLUGIN_REGISTRY", opr.PLUGIN_REGISTRY.copy()):
      del opr.PLUGIN_REGISTRY["TestOutputPluginWithArgs"]

      deserialized = rdf_output_plugin.OutputPluginDescriptor()
      deserialized.ParseFromString(serialized)

      self.assertTrue(deserialized.GetPluginClass(),
                      output_plugin.UnknownOutputPlugin)
      # UnknownOutputPlugin should just return serialized arguments as bytes.
      self.assertEqual(deserialized.plugin_args,
                       descriptor.plugin_args.SerializeToString())


class TestOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, responses):
    pass


class TestOutputPluginVerifier(output_plugin.OutputPluginVerifier):

  def VerifyHuntOutput(self, plugin, hunt):
    if hunt.runner_args.description == "raise":
      raise RuntimeError("oh no")

    return output_plugin.OutputPluginVerificationResult(
        status_message=hunt.runner_args.description)


class OutputPluginVerifierTest(test_lib.GRRBaseTest):
  """Tests for OutputPluginVerifier."""

  def _CreateHunt(self, description):
    output_plugins = [
        rdf_output_plugin.OutputPluginDescriptor(plugin_name="TestOutputPlugin")
    ]
    with implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__),
        output_plugins=output_plugins,
        description=description,
        client_rate=0,
        token=self.token) as hunt:
      return hunt

  def _GetPlugin(self, hunt):
    results_metadata = aff4.FACTORY.Open(
        hunt.urn.Add("ResultsMetadata"), token=self.token)

    plugins = results_metadata.Get(results_metadata.Schema.OUTPUT_PLUGINS)
    descriptor, state = next(itervalues(plugins))

    return descriptor.GetPluginForState(state)

  def setUp(self):
    super(OutputPluginVerifierTest, self).setUp()
    self.verifier = TestOutputPluginVerifier()

  def testMultiVerifyHuntOutputCallsVerifyHuntOutputIteratively(self):
    hunt1 = self._CreateHunt("desc1")
    plugin1 = self._GetPlugin(hunt1)

    hunt2 = self._CreateHunt("desc2")
    plugin2 = self._GetPlugin(hunt2)

    hunt3 = self._CreateHunt("desc3")
    plugin3 = self._GetPlugin(hunt3)

    results = list(
        self.verifier.MultiVerifyHuntOutput([(plugin1, hunt1), (plugin2, hunt2),
                                             (plugin3, hunt3)]))

    self.assertEqual(len(results), 3)

    self.assertEqual(results[0][0], hunt1.urn)
    self.assertEqual(results[0][1].status_message, "desc1")

    self.assertEqual(results[1][0], hunt2.urn)
    self.assertEqual(results[1][1].status_message, "desc2")

    self.assertEqual(results[2][0], hunt3.urn)
    self.assertEqual(results[2][1].status_message, "desc3")

  def testMultiVerifyHuntOutputRaisesIfVerifyHuntOutputRaises(self):
    # TestOutputPluginVerifier will raise on this one.
    hunt1 = self._CreateHunt("raise")
    plugin1 = self._GetPlugin(hunt1)

    with self.assertRaises(output_plugin.MultiVerifyHuntOutputError):
      _ = list(self.verifier.MultiVerifyHuntOutput([(plugin1, hunt1)]))

  def testMultiVerifyHuntOutputContinuesVerifyingIfExceptionOccurs(self):
    hunt1 = self._CreateHunt("desc1")
    plugin1 = self._GetPlugin(hunt1)

    hunt2 = self._CreateHunt("raise")
    plugin2 = self._GetPlugin(hunt2)

    hunt3 = self._CreateHunt("desc3")
    plugin3 = self._GetPlugin(hunt3)

    results = []
    with self.assertRaisesRegexp(output_plugin.MultiVerifyHuntOutputError,
                                 "oh no"):
      for hunt_urn, verification_result in self.verifier.MultiVerifyHuntOutput(
          [(plugin1, hunt1), (plugin2, hunt2), (plugin3, hunt3)]):
        results.append((hunt_urn, verification_result))

    self.assertEqual(len(results), 2)

    self.assertEqual(results[0][0], hunt1.urn)
    self.assertEqual(results[0][1].status_message, "desc1")

    self.assertEqual(results[1][0], hunt3.urn)
    self.assertEqual(results[1][1].status_message, "desc3")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
