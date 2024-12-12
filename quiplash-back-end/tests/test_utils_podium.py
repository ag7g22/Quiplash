import unittest
import requests
import json
from azure.cosmos import CosmosClient
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential

from shared_code.utils import utils

class test_utils_podium(unittest.TestCase):
    """
    This test set focuses on testing the responses from the server on the UtilsPodium function.
    """

    # URLS to test on
    LOCAL_DEV_URL = "http://localhost:7071/utils/podium"
    PUBLIC_URL = "https://quiplash-ag7g22.azurewebsites.net/utils/podium"
    TEST_URL = PUBLIC_URL

    # Need the update URL for updating values
    LOCAL_PLAYER_UPDATE_URL = "http://localhost:7071/player/update/"
    PUBLIC_PLAYER_UPDATE_URL = "https://quiplash-ag7g22.azurewebsites.net/player/update/"
    TEST_UPDATE_URL = PUBLIC_PLAYER_UPDATE_URL

    # Configure the Proxy objects from the local.settings.json file.
    with open('local.settings.json') as settings_file:
        settings = json.load(settings_file)
    FUNCTION_KEY = settings['Values']['FunctionAppKey']
    MyCosmos = CosmosClient.from_connection_string(settings['Values']['AzureCosmosDBConnectionString']) # Cosmos Object
    QuiplashProxy = MyCosmos.get_database_client(settings['Values']['DatabaseName']) # Proxy object for Quiplash database
    PlayerContainerProxy = QuiplashProxy.get_container_client(settings['Values']['PlayerContainerName']) # Proxy obj for Player container
    PromptContainerProxy = QuiplashProxy.get_container_client(settings['Values']['PromptContainerName']) # Proxy obj for Prompt container
    TranslatorProxy = TextTranslationClient(endpoint=settings['Values']['TranslationEndpoint'], 
                                            credential=AzureKeyCredential(settings['Values']['TranslationKey'])) # proxy for Translator
    utility = utils()

    # SetUp method executed before each test       
    def setUp(self):
        pass

    # tearDown method executed before each test
    # @unittest.skip
    def tearDown(self) -> None:
        # Get rid of all the items inbetween tests.
        for doc in self.PlayerContainerProxy.read_all_items():
            self.PlayerContainerProxy.delete_item(item=doc,partition_key=doc['id'])
        for doc in self.PromptContainerProxy.read_all_items():
            self.PromptContainerProxy.delete_item(item=doc,partition_key=doc['username'])

    def test_player_list(self):
        # Register players
        self.PlayerContainerProxy.create_item({"id": "1", "username" : "antoni_gn", "password": "ILoveTricia" , "games_played" : 10 , "total_score" : 40   })
        self.PlayerContainerProxy.create_item({"id": "2", "username" : "Jayranas", "password": "AA_Batteries" , "games_played" : 20 , "total_score" : 80   })
        self.PlayerContainerProxy.create_item({"id": "3", "username" : "Jsidssjdisdfjsndsn", "password": "ChaewonChaewon" , "games_played" : 10 , "total_score" : 40   })
        self.PlayerContainerProxy.create_item({"id": "4", "username" : "Chaxluc09", "password": "Cuphead" , "games_played" : 10 , "total_score" : 80   })
        self.PlayerContainerProxy.create_item({"id": "5", "username" : "ApoCalysE", "password": "Acineratortron" , "games_played" : 50 , "total_score" : 100   })
        self.PlayerContainerProxy.create_item({"id": "6", "username" : "pwelwez", "password": "CombustingToilets" , "games_played" : 10 , "total_score" : 40   })
        self.PlayerContainerProxy.create_item({"id": "7", "username" : "lesacafe", "password": "river" , "games_played" : 1 , "total_score" : 10   })

        # Update player values
        dict_update_6 = {"username": "pwelwez", "add_to_games_played": 0, "add_to_score" : -30 }
        response_6 = requests.put(self.TEST_UPDATE_URL,params={"code": self.FUNCTION_KEY},json=dict_update_6)
        self.assertEqual(200,response_6.status_code)

        dict_update_7 = {"username": "lesacafe", "add_to_games_played": 9, "add_to_score" : 0 }
        response_7 = requests.put(self.TEST_UPDATE_URL,params={"code": self.FUNCTION_KEY},json=dict_update_7)
        self.assertEqual(200,response_7.status_code)

        # Check if function responds.
        podium_response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY})
        self.assertEqual(200,podium_response.status_code)

        # Check if dictionary is in correct order.
        actual_dict = podium_response.json()
        expected_dict = {'gold': [{'username': 'Chaxluc09', 'games_played': 10, 'total_score': 80}], 
                         'silver': [{'username': 'antoni_gn', 'games_played': 10, 'total_score': 40}, {'username': 'Jsidssjdisdfjsndsn', 'games_played': 10, 'total_score': 40}, {'username': 'Jayranas', 'games_played': 20, 'total_score': 80}], 
                         'bronze': [{'username': 'ApoCalysE', 'games_played': 50, 'total_score': 100}]} 
        
        self.assertEqual(expected_dict,actual_dict)
        

    # @unittest.skip
    def test_tied_player_list(self):
        self.PlayerContainerProxy.create_item({"id": "1", "username" : "antoni_gn", "password": "ILoveTricia" , "games_played" : 10 , "total_score" : 80   })
        self.PlayerContainerProxy.create_item({"id": "8", "username" : "banana_boi", "password": "ILoveTricia" , "games_played" : 10 , "total_score" : 40   })
        self.PlayerContainerProxy.create_item({"id": "9", "username" : "ghostlysandvich", "password": "ILoveTricia" , "games_played" : 10 , "total_score" : 40   })
        self.PlayerContainerProxy.create_item({"id": "10", "username" : "eddgerant", "password": "ILoveTricia" , "games_played" : 0 , "total_score" : 0   })
        
        # Check if function responds.
        podium_response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY})
        self.assertEqual(200,podium_response.status_code)

        # Check if dictionary is in correct order.
        actual_dict = podium_response.json()
        expected_dict = {'gold': [{'username': 'antoni_gn', 'games_played': 10, 'total_score': 80}], 
                         'silver': [{'username': 'banana_boi', 'games_played': 10, 'total_score': 40}, {'username': 'ghostlysandvich', 'games_played': 10, 'total_score': 40}], 
                         'bronze': [{'username': 'eddgerant', 'games_played': 0, 'total_score': 0}]} 
        
        self.assertEqual(expected_dict,actual_dict)