import unittest
import requests
import json
from azure.cosmos import CosmosClient
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential

from shared_code.player import player
from shared_code.prompt import prompt
from shared_code.utils import utils

class test_utils_get(unittest.TestCase):
    """
    This test set focuses on testing the responses from the server on the UtilsGet function.
    """

    # URLS to test on
    LOCAL_DEV_URL = "http://localhost:7071/utils/get"
    PUBLIC_URL = "https://quiplash-ag7g22.azurewebsites.net/utils/get"
    TEST_URL = PUBLIC_URL

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

    # Valid players
    player_1 = player(player_proxy=PlayerContainerProxy,username="antoni_gn",password="ILoveTricia")
    player_2 = player(player_proxy=PlayerContainerProxy,username="Jayranas",password="AA_Batteries")
    player_3 = player(player_proxy=PlayerContainerProxy,username="Jsidssjdisdfjsndsn",password="ChaewonChaewon")
    player_4 = player(player_proxy=PlayerContainerProxy,username="Chaxluc09",password="Cuphead")

    # Valid Prompts
    prompt_1 = prompt(player_proxy=PlayerContainerProxy,trans_proxy=TranslatorProxy,text="The most useless Python one-line program", username="antoni_gn")
    prompt_2 = prompt(player_proxy=PlayerContainerProxy,trans_proxy=TranslatorProxy,text="Why the millenial crossed the avenue?", username="antoni_gn")
    prompt_3 = prompt(player_proxy=PlayerContainerProxy,trans_proxy=TranslatorProxy,text="Why the ka-boomer crossed the road?", username="Jayranas")
    prompt_4 = prompt(player_proxy=PlayerContainerProxy,trans_proxy=TranslatorProxy,text="Why the boomer crossed the road?", username="Jsidssjdisdfjsndsn")

    # SetUp method executed before each test       
    def setUp(self):
        # Register players and their prompts
        self.PlayerContainerProxy.create_item(self.player_1.to_dict())
        self.PlayerContainerProxy.create_item(self.player_2.to_dict())
        self.PlayerContainerProxy.create_item(self.player_3.to_dict())
        self.PlayerContainerProxy.create_item(self.player_4.to_dict())
        

        self.PromptContainerProxy.create_item(self.prompt_1.to_dict())
        self.PromptContainerProxy.create_item(self.prompt_2.to_dict())
        self.PromptContainerProxy.create_item(self.prompt_3.to_dict())
        self.PromptContainerProxy.create_item(self.prompt_4.to_dict())

    # tearDown method executed before each test
    # @unittest.skip
    def tearDown(self) -> None:
        # Get rid of all the items inbetween tests.
        for doc in self.PlayerContainerProxy.read_all_items():
            self.PlayerContainerProxy.delete_item(item=doc,partition_key=doc['id'])
        for doc in self.PromptContainerProxy.read_all_items():
            self.PromptContainerProxy.delete_item(item=doc,partition_key=doc['username'])

    def test_input_with_prompts(self):
        # Request for player_1 and player_3 in english
        request = {"players" : ["antoni_gn","Jsidssjdisdfjsndsn"], "language": "en"}
        response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        dict_expected = [{'id': self.prompt_1.id, 'text': 'The most useless Python one-line program', 'username': 'antoni_gn'}, 
                         {'id': self.prompt_2.id, 'text': 'Why the millenial crossed the avenue?', 'username': 'antoni_gn'}, 
                         {'id': self.prompt_4.id, 'text': 'Why the boomer crossed the road?', 'username': 'Jsidssjdisdfjsndsn'}]

        # Check if you got the OK response for successful login.
        self.assertEqual(dict_response,dict_expected)

    def test_input_player_no_prompt(self):
        # Request for player_4, who doesn't have any prompts
        request = {"players" : ["Chaxluc09"], "language": "en"}
        response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        self.assertEqual(dict_response,[])

    def test_input_non_existent_player(self):
        # Request for player_2 and a non-register player, it should still output player_2's prompts
        request = {"players" : ["Jayranas", "JayranasGF"], "language": "es"}
        response = requests.get(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        dict_expected = [{'id': self.prompt_3.id, 'text': '¿Por qué el ka-boomer cruzó la calle?', 'username': 'Jayranas'}]

        self.assertEqual(dict_response,dict_expected)
