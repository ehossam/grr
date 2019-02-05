# This is the controller
# It is supposed to govern all interactions between the acauthority and client, and the acauthority and
# server


# Activity Diagram Flow

# Server sends acauthority a request for an access token for certain number of named resources
# on the
# client machine

# The acauthority uses the keycloak in the backend to verify the role of the server user and the
# access granted
# Access classes and roles will be heirarchical, meaning they will start out at the easiest
# config and then go down with more complexity and freedom of choice
# Assumed : Identity has been received

# Returns roles of the identity using the KeyCloak api
# args : identity is a certificate signed by a CA


# New Architecture
#  The acauthority is inlined
# Which means it acts as the server in the past architecture
# We need to check the role
# And the action(s) acquired by that role and if the action required is included in the actions acquired
# No more tokens

# The deployment Implementation of the acauthority will not follow the same as the server
# To be examined is the server-client communication because it should be cloned for the server-ac-client
# Architecture
# import keycloak
# x = KeyCloak.client
# keycloak.KeycloakAdmin.create_client(x)


# abstractions
# keycloak clients are apps generally but they are the server analysts
# Just to assign to each of them a role
# Then a user account is managed by the client with the available role

# The server analyst will be the client trying to access the users with certain roles
# The roles will be just a database of tags, the tags will be analyzed using the controller
# TODO: Check what would happen when there are non conventional roles, where to check the roles actions
# TODO: adopt the grr terminology when dealing with clients in keycloak and refer to them as analysts
# TODO: Figure out a way to be able to keep the connection open with the underlying keycloak server
# TODO: Might it not be a good idea to keep track of the machines and just keep track of the server analysts ids
# TODO: in request handlers firstly check if the request contains the needed parameters to be processed so that
# a faulty request does not break the entire system
# TODO: ACAuth functionalities:
# It can respond to incoming reqs
    #                 asking for approving tokens sent by analysts
    #                 asking for creating roles for clients
    #                 asking for modifying roles for clients
    #                 asking for deleting clients certain roles
    #                 asking for refershing tokens for server analyst

# The new implementation suggests that all machines in the grr scope are keycloak clients such that each client
# can have roles
# keycloak users are to assume the roles used by the client
# The assumption is that the client will have to create the roles and the server analyst will send a request
# to assume the certain role it needs from the client and only those roles will be available for useage
# Also be aware that in this scheme there is no specific relationship between the client and the server analyst
# or the server for that matter, except for the binary being available and referencable for the server

# TODO: It is a good idea to transform this web server into an async one and use callbacks instead of just
# waiting on requests

# TODO: Most probably we will need to have a standalone web server
# Component to handle the logic of the ac and not just keycloak on its
# own even if we could just use a REST API for clients, still we would
# need something to make sure that we are using roles (whether issued
# or created ) that actually have a terminal(theory of computing sense
# ) symbol, ie we need to have an underlying representation of what each
# role means

# TODO: Delete all of the non-keyclaok-API-using functions and classes and limit the usage to
# keycloak
# TODO: The keycloak api can be used to incorporate the required data for access and might have
# fields for extra information which will be used to encode the flow, which can be of two types
# either it is a fundamental type of the supported flows and then the access required for the flow
# will be determined
# TODO: encode access lvls in terms of the flows
# Flow
# client -> action -> acauth -> databases -> client role -> approve/deny role ->

# TODO: We shifted from having any possible interaction from the client and server with the ac authority to just
# having the ac authority being an access point to register through, the server and the client will register
# then all incoming traffic will use rpc after registering and authenticating the server and client
# TODO: To use the rpc in the grr server and client we have to register the methods of the ac server (
# which are just keycloak objects methods) as dispatcher methods in the json-rpc module dispatcher
# This can be done if we can list all of the functions one by one of all the classes in the module and then
# use the syntax func = dec(func) here dec() is the add_method decorator used by the jsonrpc dispatcher

# VERY IMPORTANT
# TODO: The way to use json-rpc is to firstly initiate the dispatcher and then call add_object on a
# keycloak admin object which will then include all needed methods of the object for rpc in the ac side from
# the keycloak client(grr client) or keycloak user (grr server)

# TODO: Might be a good idea to actually let the client and server (GRR) to call RPC on the registration and
# Authentication and remove that code completely from the server side since it will also be in the client side
# and just authenticate the server here and then let the client and server RPC on the methods of the
# keycloak_admin

import keycloak
import http.server
import requests, json
import inspect # To be able to list all function pointers for them to be registrable in the rpc pool
from accesslvl_identifier import *
from request_types import *
from httpserverconfig import *
from jsonrpc import JSONRPCResponseManager, dispatcher

class ACAuthority:
    # Needed because the server apparently kicks us out every few ms, oh well such is life ....
    def auth(self):
        self.adminobj = keycloak.keycloak_admin.KeycloakAdmin("http://localhost:8080/auth/", self.admin_user_name, self.admin_password)

    # TODO: May be this should be moved into a different class, something in __init__.py
    def register_functions_in_jsonrpc(self):
        """This function will register the entire keycloak api in the rpc pool (the list of all the methods call
        able from rpc)
        :returns: nothing for the time being

        """
        keycloak_admin_methods = inspect.getmembers(self.adminobj, predicate=inspect.ismethod) # list
        for amethod in keycloak_admin_methods:
            amethod[1] = dispatcher.add_method(amethod[1])
        pass
    # This should be remove in favor of an initialization and installation script
    def __init__(self):
        # AC Authority initialization
        # It should firstly get access to the admin account of keycloak
        # TODO: Initializing the listening thread ...
        # TODO: move this into a different class to be just serving and has nothing to do with the controll
        # On a second note just async the hell out of this server
        # TODO: Add a command execution to spawn up the server if it si not already spawned

        self.port = ACAUTHORITY_HTTP_SERVERPORT
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", self.port), handler) as httpd:
            print("serving at port", self.port)
            httpd.serve_forever()
        # these to be extracted from config files (Most probably YAML), and lets try encrypting them
        self.admin_user_name = "admin"
        self.admin_password = "9437618525"
        self.auth()

    # This is going to be moved into the incomingrequesthandler
    # TODO: This might need to be removed in using the rpc instead of the old client-server implementation
    # except for actually the registration part, that has to go through some checking, and also ther should be
    # a legalizer for us, to check if the proposed role is actually legal, or actually we can enforce that the
    # client (grr client) will have to choose in the interface a set of flows to include in the access role
    # made available to assumers

    def dispatch(self, request):
        """This function is supposed to handle the requests types based on the sender and what they
        are trying to acheive, most likely it will be just a server analyst or a client machine and
        the purpose of the request can be to set the highest access role rights for the specific client
        machine which any server machine that has access to the client machine can use to execute commands
        in the client side

        :request: http request carrying mostly json data to be parsed into an ac(access control) action
        whether it will be to create a new role on behalf of the client or to actually assume a role via
        verifying the access levels of the role assumed by the server analyst sending the request against
        the available and permissable access rights provided by the role specified by the client role
        :returns: nothing, just calls the appropriate function with the appropriate arguments

        """
        req_type = request.req_type
        if req_type == ApproveTokenReq:
            self.approve_toke(token)
            pass
        if req_type == CreateRoleReq:
            self.create_role(request.client, request.role)
            pass
        if req_type == ModifyClientRolesReq:
            self.modyify_client_roles(request.client, request.new_role)
        if req_type == RefreshTokenReq:
            self.refresh_token(request.token)
            pass
        pass

    def refresh_token(self, token):
        """takes a token and checks the validity of it probably after rechecking the identity of the server user
        TODO which might be in a separate function on its own to be transferable in all functions and executable
        in all of them as a preface to normal operation just to be clear out of any authorization issues and then
        sends a new token to the sender via using the keycloak api to generate a new token

        Note this token is not an access token it is rather the token granted to the user to carry the
        a client role

        :token: TODO
        :returns: TODO

        """
        if token.exp_date < current_date: # This really should not be less than but rather a data related operation, mayb keycloak offers a fresh()
            return token
        else:
            keycloak.create_new_token(token)
            pass
    def approve_token(self, token):
        """this function will handle the token and check if it is valid as the sender claims and then check the
        role asssumed by the sender onto the receiver end then either send back a response saying yes it is valid
        or sending back a response saying no it isnot
        also this is supposed to be a callback function for the async http server

        :token: a keycloak access token with an assumed role, can be refereshed, this is not an initial access token or a beared token, this is a token in the sense that an admin server analyst can use to assume roles
        :returns: an http response

        """
        token_id = token.id
        sender = token.senderid
        issuer = token.issuerid # this should be the same as the admin keycloak id
        if issuer == self.adminobj.client_id:
            # TODO: Look for a keycloak api to substitute for checking
            # manual
            # This means it is approved
            # Because the issuer is actually the ac auth
            # Send back a response with http code 200 ok or an authorized flag sent back of some sort
            return
            pass
        else:
            # This means it is not approved
            # use requests lib to send a response with 401 unauthorized tag to the sender
            pass
        pass

    def create_role_req(self, client, role):
        """create a role if possible for the client in the request with the specific access rights in keycloak


        :client: client id to be checked against the sender TODO check also the credentials
        :role: new role explaining the access rights granted to the user of the role and this role checked for actual viability to be represented in terms of the available actions and flows
        :returns: boolean if the role is created or not

        """
        # Firstly check if the role is legal
        access_lvl_identifier = AccessLvlIdentifier() # new instance of the identifier
        if access_lvl_identifier.access_lvl_appropriate(role):
            created_role = self.adminobj.create_client_role()
        return created_role

    def modyify_client_roles(client, new_role):
        """checks if the client has that role and then checks if the available new role and new access rights
        associated with the role can be applied

        :returns: TODO
        """
        pass
    # TODO: From down here, probably deprecated
    # This is deprecated because the actions are no longer our main issue here, but rather the flow
    # def request_action(self,request):
    #     self.auth()
    #     return request.action

    def requester(self, request):
        self.auth()
        return request.analyst

    def targeted_client(self, request):
        self.auth()
        return request.request_machine

    def requested_role(self, request):
        self.auth()
        analyst = self.request_analyst(request)
        return self.adminobj.get_client_roles(analyst)

    # TODO: why do we have this ?????
    def identity_as_db_entry(self,identity):
        self.auth()

    def get_identity(self, request):
        self.auth()
        current_users = self.adminobj.get_users()
        db_entry = self.identity_as_db_entry(self.request)

    # TODO: What is this supposed to do ?????
    def facilitate_roles(self, request):
        self.auth()
        identity = self.get_identity(request)

    # DEPRECATED or is it ?
    def identity_roles(self,server_IP):
        self.auth()
        realm_groups = self.adminobj.get_groups()
        # The single group is a client in our definition and the users in the group are the server analysts
        # subscribed to roles to be used analyzing the client machine
        for group in realm_groups:
            pass
        pass




