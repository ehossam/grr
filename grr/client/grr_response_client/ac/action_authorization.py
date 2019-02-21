from grr_response_ac import config
from grr_response_client.gui import access_control_agent
from grr_response_client.actions import ActionPlugin
from keycloak import KeycloakOpenID
from config import KEYCLOAK_CLIENT
from tkinter import *
import thread

import requests
import jwt

# Need to be globally accessible for the current client context
# so the gui can access it
# whitelisted_actions init

actions_whitelist = dict().fromkeys(ActionPlugin.classes.keys(), True)
# actions_whitelist = dict().fromkeys(ActionPlugin.classes.keys())
# root = Tk()
# actions_whitelist = ActionPlugin.classes.keys()
# actions_whitelist = {anaction: BooleanVar(root) for anaction in actions_whitelist}
# actions_list_gui = access_control_agent.Checklist(root, actions_whitelist)
# actions_list_gui.pack(side=LEFT)
# actions_list_gui.config(relief=GROOVE, bd=2)
# print(actions_whitelist)
# Init GUI
# TODO(ahmednofal): Remove from here

# TODO(ahmednofal): Remove, just testing same context
# for action_entry, accessible in actions_whitelist.items():
#         print(action_entry , " is ", accessible.get())
# actions_list_gui.pack(side=TOP,  fill=X)
# thread.start_new_thread(newthread_for_gui, ())
# try:
#         thread.start_new_thread(root.mainloop, (root, ))
# except:
#         print("got an except")
# root.mainloop()



def action_accessible(action):
        """
        checks if the action exists in the whitelisted
        actions defined in the grr_response_client.ac.config file
        """
        # TODO(ahmednofal): Separate gui from the ac
        try: 
                valuetoreturn = actions_whitelist[action].get()
        except:
                valuetoreturn = actions_whitelist[action]
        return valuetoreturn

class ACServerCommunicator:
    def __init__(self, hostname = None, port = None):
        keycloak_openid = KeycloakOpenID(
            server_url=ACSERVER['server_url'],
            realm_name=ACSERVER['realm'],
            # this is the client id, we do not need it
            client_id="",
            # client secret no need
            client_secret_key="")

        config_well_know = keycloak_openid.well_know()
        self.registration_endpoint = config_well_know['registration_endpoint']
        # using here the REST API because keycloak would need admin
        # obj to be able to regsiter the client into keycloak
    def register_client(self):
        self.registration_bearer_token=KEYCLOAK_CLIENT['bearer_token']
        # make sure during installation that the Keycloak client gets the same
        # grr_response_client ID (cliend ID is the same in both servers,
        # keycloak and grr)
        response = requests.post(url=self.registration_endpoint,
                                 data={'client_name':self.client_name},
                                 headers={
                                     'Content-Type':'application/json',
                                     'Authorization' : 'bearer'+' '+ \
                                     self.registration_bearer_token
                                 })
        response = response.json()
        self.bearer_token = response['registration_access_token']
        # TODO: Before that the client has to be enabled for direct
        # access first otherwise users will fail
        # The keycloak openid api is most probably used for the users
        # not the clients as we thought, for the clients we will use
        # the requests api and try to use the admin_rest_api to add or
        # remove roles and update the client
        return self.bearer_token

    def fresh(self, token):
        """this function takes a token and checks if it is currently
        fresh or not """
        raise NotImplementedError

    def token_verified(self, token, action_name):
        jwt_token_decoded = jwt.decode(token,
                                      ACSERVER['public_key'],
                                      algorithms = [encryption_algorithm])
        # TODO: Should check if the token is fresh, my pyjwt has a way
        return action_name == jwt_token_decoded['action']







