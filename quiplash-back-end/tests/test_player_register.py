import unittest
import requests
import json
from azure.cosmos import CosmosClient

class test_player_register(unittest.TestCase):
    """
    This test set focuses on testing the responses from the server on the PlayerRegister function.
    """
    # URLS to test on
    LOCAL_DEV_URL = "http://localhost:7071/player/register"
    PUBLIC_URL = "https://quiplash-ag7g22.azurewebsites.net/player/register"
    TEST_URL = LOCAL_DEV_URL

    # Configure the Proxy objects from the local.settings.json file.
    with open('local.settings.json') as settings_file:
        settings = json.load(settings_file)
    FUNCTION_KEY = settings['Values']['FunctionAppKey']
    MyCosmos = CosmosClient.from_connection_string(settings['Values']['AzureCosmosDBConnectionString']) # Cosmos Object
    QuiplashProxy = MyCosmos.get_database_client(settings['Values']['DatabaseName']) # Proxy object for Quiplash database
    PlayerContainerProxy = QuiplashProxy.get_container_client(settings['Values']['PlayerContainerName']) # Proxy obj for Player container

    # tearDown method executed before each test
    def tearDown(self) -> None:
        # Get rid of all the items inbetween tests.
        for doc in self.PlayerContainerProxy.read_all_items():
            self.PlayerContainerProxy.delete_item(item=doc,partition_key=doc['id'])

    def test_register_good_player(self):
        # Send a request to register player. (Input is a dictionary)
        request = {"username": "antoni_gn", "password": "ILoveTricia"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Check if you actually got OK response for good player.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTricia","games_played": 0,"total_score": 0})


    #@unittest.skip
    def test_register_short_username(self):
        # Send a request to register player, which has an INVALID USERNAME length. (Input is a dictionary)
        request = {"username": "anto", "password": "ILoveTricia"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Response alerts the username is invalid.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Username less than 5 characters or more than 15 characters')



    #@unittest.skip
    def test_register_username_in_boundary_1(self):
        # Send a request to register player. (Input is a dictionary)
        request = {"username": "anton", "password": "ILoveTricia"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Check if you actually got OK response for good player.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "anton") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "anton","password": "ILoveTricia","games_played": 0,"total_score": 0})



    #@unittest.skip
    def test_register_username_in_boundary_2(self):
        # Send a request to register player. (Input is a dictionary)
        request = {"username": "antoni_gnnnnnnn", "password": "ILoveTricia"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Check if you actually got OK response for good player.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gnnnnnnn") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gnnnnnnn","password": "ILoveTricia","games_played": 0,"total_score": 0})


    #@unittest.skip
    def test_register_long_username(self):
        # Send a request to register player, which has an INVALID USERNAME length. (Input is a dictionary)
        request = {"username": "antoni_gnnnnnnnn", "password": "ILoveTricia"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Response alerts the username is invalid.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Username less than 5 characters or more than 15 characters')


    #@unittest.skip
    def test_register_short_password(self):
        # Send a request to register player, which has an INVALID PASSWORD length. (Input is a dictionary)
        request = {"username": "antoni_gn", "password": "ILov"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Response alerts that the password is invalid.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Password less than 8 characters or more than 15 characters')


    #@unittest.skip
    def test_register_long_password(self):
        # Send a request to register player, which has an INVALID PASSWORD length. (Input is a dictionary)
        request = {"username": "antoni_gn", "password": "ILoveTriciaaaaaa"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Response alerts that the password is invalid.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Password less than 8 characters or more than 15 characters')


    def test_register_password_boundary_1(self):
        # Send a request to register player. (Input is a dictionary)
        request = {"username": "antoni_gn", "password": "ILoveTri"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Check if you actually got OK response for good player.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTri"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTri","games_played": 0,"total_score": 0})


    def test_register_password_boundary_2(self):
        # Send a request to register player. (Input is a dictionary)
        request = {"username": "antoni_gn", "password": "ILoveTriciaaaaa"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()     

        # Check if you actually got OK response for good player.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTriciaaaaa"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTriciaaaaa","games_played": 0,"total_score": 0})


    #@unittest.skip
    def test_register_existing_player(self):
        # Send a request for the same player twice.
        request = {"username": "antoni_gn", "password": "ILoveTricia"}
        response_1 = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)
        self.assertEqual(200,response_1.status_code)
        dict_response_1 = response_1.json()   

        # Response successfully adds player_1.
        self.assertTrue(dict_response_1['result'])
        self.assertEqual(dict_response_1['msg'],'OK')

        # Same player again
        response_2 = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)
        self.assertEqual(200,response_2.status_code)
        dict_response_2 = response_2.json()

        # Response successfully sends error as player_1 was already added.
        self.assertFalse(dict_response_2['result'])
        self.assertEqual(dict_response_2['msg'],'Username already exists')
