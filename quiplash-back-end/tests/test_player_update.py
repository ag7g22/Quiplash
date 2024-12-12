import unittest
import requests
import json
from azure.cosmos import CosmosClient
from shared_code.player import player

class test_player_update(unittest.TestCase):
    """
    This test set focuses on testing the responses from the server on the PlayerUpdate function.
    """
    # URLS to test on
    LOCAL_DEV_URL = "http://localhost:7071/player/update"
    PUBLIC_URL = "https://quiplash-ag7g22.azurewebsites.net/player/update"
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
    # @unittest.skip
    def tearDown(self) -> None:
        # Get rid of all the items inbetween tests.
        for doc in self.PlayerContainerProxy.read_all_items():
            self.PlayerContainerProxy.delete_item(item=doc,partition_key=doc['id'])


    def test_update_good_player(self):
        # Test the newly created player has total_score, games_played = 0
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTricia","games_played": 0,"total_score": 0})


        # Update this player's info
        dict_update = {"username": "antoni_gn", "add_to_games_played": 10, "add_to_score" : 2600 }
        response = requests.put(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_update)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check if you got the OK response for update.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTricia","games_played": 10,"total_score": 2600})


    def test_update_nonexistent_player(self):
        # Try a login with non existent player
        dict_update = {"username": "chaxluc09", "add_to_games_played": 10, "add_to_score" : 2600 }
        response = requests.put(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_update)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check if you got reply that player doesn't exist.
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],"Player does not exist")



    def test_update_negative_games_played(self):
        # Test the newly created player has total_score, games_played = 0
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTricia","games_played": 0,"total_score": 0})


        # Update this player's info
        dict_update = {"username": "antoni_gn", "add_to_games_played": -1, "add_to_score" : 100 }
        response = requests.put(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_update)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check if you got the OK response for successful login.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTricia","games_played": 0,"total_score": 100})


    def test_update_negative_total_score(self):
        # Test the newly created player has total_score, games_played = 0
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTricia","games_played": 0,"total_score": 0})


        # Update this player's info
        dict_update = {"username": "antoni_gn", "add_to_games_played": 10, "add_to_score" : -100 }
        response = requests.put(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=dict_update)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()   

        # Check if you got the OK response for successful login.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "antoni_gn") AND player.password = "ILoveTricia"'
        query_result = list(self.PlayerContainerProxy.query_items(query=query, enable_cross_partition_query=True))
        query_result_stripped = [{"username": item['username'], "password": item['password'], 
                                 "games_played": item['games_played'], "total_score": item['total_score']}
                                 for item in query_result]
        self.assertEqual(query_result_stripped[0],{"username": "antoni_gn","password": "ILoveTricia","games_played": 10,"total_score": 0})