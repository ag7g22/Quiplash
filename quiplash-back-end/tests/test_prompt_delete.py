import unittest
import requests
import json
from azure.cosmos import CosmosClient
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential

from shared_code.player import player
from shared_code.prompt import prompt

class test_prompt_delete(unittest.TestCase):
    """
    This test set focuses on testing the responses from the server on the PromptDelete function.
    """

    # URLS to test on
    LOCAL_DEV_URL = "http://localhost:7071/prompt/delete"
    PUBLIC_URL = "https://quiplash-ag7g22.azurewebsites.net/prompt/delete"
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

    # Valid players
    player_1 = player(player_proxy=PlayerContainerProxy,username="antoni_gn",password="ILoveTricia")
    player_2 = player(player_proxy=PlayerContainerProxy,username="Jayranas",password="AA_Batteries")
    player_3 = player(player_proxy=PlayerContainerProxy,username="Jsidssjdisdfjsndsn",password="ChaewonChaewon")

    # Valid Prompts
    prompt_1 = prompt(player_proxy=PlayerContainerProxy,trans_proxy=TranslatorProxy,text="The most useless Python one-line program", username="antoni_gn")
    prompt_2 = prompt(player_proxy=PlayerContainerProxy,trans_proxy=TranslatorProxy,text="Why the millenial crossed the avenue?", username="antoni_gn")
    prompt_3 = prompt(player_proxy=PlayerContainerProxy,trans_proxy=TranslatorProxy,text="Why the ka-boomer crossed the road?", username="Jayranas")

    # SetUp method executed before each test       
    def setUp(self):
        # Register players and their prompts
        self.PlayerContainerProxy.create_item(self.player_1.to_dict())
        self.PlayerContainerProxy.create_item(self.player_2.to_dict())
        self.PlayerContainerProxy.create_item(self.player_3.to_dict())

        self.PromptContainerProxy.create_item(self.prompt_1.to_dict())
        self.PromptContainerProxy.create_item(self.prompt_2.to_dict())
        self.PromptContainerProxy.create_item(self.prompt_3.to_dict())

    # tearDown method executed before each test
    # @unittest.skip
    def tearDown(self) -> None:
        # Get rid of all the items inbetween tests.
        for doc in self.PlayerContainerProxy.read_all_items():
            self.PlayerContainerProxy.delete_item(item=doc,partition_key=doc['id'])
        for doc in self.PromptContainerProxy.read_all_items():
            self.PromptContainerProxy.delete_item(item=doc,partition_key=doc['username'])

    def test_delete_0_prompt(self):
        # Send the request to delete prompts by player_1
        request = {"player": "Jsidssjdisdfjsndsn"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json() 

        # Check if deleted the DB as follows:
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'0 prompts deleted')


    def test_delete_1_prompt(self):
        # Send the request to delete prompts by player_1
        request = {"player": "Jayranas"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json() 

        # Check if deleted the DB as follows:
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'1 prompts deleted')


    def test_delete_2_prompts(self):
        # Send the request to delete prompts by player_1
        request = {"player": "antoni_gn"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json() 

        # Check if deleted the DB as follows:
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'2 prompts deleted')