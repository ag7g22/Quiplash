import unittest
import requests
import json
from azure.cosmos import CosmosClient
from shared_code.player import player

class test_player_login(unittest.TestCase):
    """
    This test set focuses on testing the responses from the server on the PlayerLogin function.
    """
    # URLS to test on
    LOCAL_DEV_URL = "http://localhost:7071/player/login"
    PUBLIC_URL = "https://quiplash-ag7g22.azurewebsites.net/player/login"
    TEST_URL = PUBLIC_URL

    # Configure the Proxy objects from the local.settings.json file.
    with open('local.settings.json') as settings_file:
        settings = json.load(settings_file)
    FUNCTION_KEY = settings['Values']['FunctionAppKey']
    MyCosmos = CosmosClient.from_connection_string(settings['Values']['AzureCosmosDBConnectionString']) # Cosmos Object
    QuiplashProxy = MyCosmos.get_database_client(settings['Values']['DatabaseName']) # Proxy object for Quiplash database
    PlayerContainerProxy = QuiplashProxy.get_container_client(settings['Values']['PlayerContainerName']) # Proxy obj for Player container

    # A valid player
    player_1 = player(player_proxy=PlayerContainerProxy,username="antoni_gn",password="ILoveTricia")

    # SetUp method executed before each test       
    def setUp(self):
        # Register player_1
        self.PlayerContainerProxy.create_item(self.player_1.to_dict())

    # tearDown method executed before each test
    def tearDown(self) -> None:
        # Get rid of all the items inbetween tests.
        for doc in self.PlayerContainerProxy.read_all_items():
            self.PlayerContainerProxy.delete_item(item=doc,partition_key=doc['id'])

    
    def test_successful_login(self):
        # Try a login with correct credentials
        dict_login = {"username": "antoni_gn", "password": "ILoveTricia"}
        response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_login)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check if you got the OK response for successful login.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')


    def test_wrong_password(self):
        # Try a login with incorrect password
        dict_login = {"username": "antoni_gn", "password": "ILoveMen"}
        response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_login)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check for invalidated credentials.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Username or password incorrect')



    def test_wrong_username(self):
        # Try a login with incorrect username
        dict_login = {"username": "antoni_gnn", "password": "ILoveTricia"}
        response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_login)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check for invalidated credentials.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Username or password incorrect')


    def test_nonexistent_player(self):
        # Try a login with non existent player
        dict_login = {"username": "lesacafe", "password": "Niko"}
        response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_login)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check for invalidated credentials.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Username or password incorrect')


    def test_wrong_pw_and_user(self):
        # Try a login with incorrect password
        dict_login = {"username": "lesacafe", "password": "ILoveMen"}
        response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_login)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check for invalidated credentials.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Username or password incorrect')