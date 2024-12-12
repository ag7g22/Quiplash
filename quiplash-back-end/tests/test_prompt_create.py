import unittest
import requests
import json
from azure.cosmos import CosmosClient
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from shared_code.player import player

class test_prompt_create(unittest.TestCase):
    """
    This test set focuses on testing the responses from the server on the PromptCreate function.
    """

    # URLS to test on
    LOCAL_DEV_URL = "http://localhost:7071/prompt/create"
    PUBLIC_URL = "https://quiplash-ag7g22.azurewebsites.net/prompt/create"
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

    # A valid player
    player_1 = player(player_proxy=PlayerContainerProxy,username="antoni_gn",password="ILoveTricia")

    # SetUp method executed before each test       
    def setUp(self):
        # Register player_1 and prepare input JSON
        self.PlayerContainerProxy.create_item(self.player_1.to_dict())

    # tearDown method executed before each test
    # @unittest.skip
    def tearDown(self) -> None:
        # Get rid of all the items inbetween tests.
        for doc in self.PlayerContainerProxy.read_all_items():
            self.PlayerContainerProxy.delete_item(item=doc,partition_key=doc['id'])
        for doc in self.PromptContainerProxy.read_all_items():
            self.PromptContainerProxy.delete_item(item=doc,partition_key=doc['username'])


    # @unittest.skip
    def test_successful_prompt_creation(self):
        # Send a valid prompt request
        text = "I'm Monkey D. Luffy and I'm going to be king of the pirates!"
        request = { "text": text, "username": "antoni_gn"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        # Check if you got the OK response.
        self.assertTrue(dict_response['result'])
        self.assertEqual(dict_response['msg'],'OK')

        # Test the DB was correctly updated
        query = 'SELECT p.id, p.username, t.text FROM prompt p JOIN t IN p.texts WHERE t.language = "en" AND t.text = "{}"'.format(text)
        query_result = list(self.PromptContainerProxy.query_items(query=query, enable_cross_partition_query=True))

        # Check if theres a query result
        self.assertNotEqual(query_result, [])

        # Retrieve item and check if the format is correct!
        id = query_result[0]['id']
        item = self.PromptContainerProxy.read_item(item=id, partition_key="antoni_gn")
        actual_result = {key: item[key] for key in item if not key.startswith("_")}
        expected_result = {"id": id,"username": "antoni_gn", "texts": [
        {"language": "en", "text": "I'm Monkey D. Luffy and I'm going to be king of the pirates!"},
        {"language": "ga", "text": "Tá mé Moncaí D. Luffy agus tá mé ag dul a bheith rí na pirates!"},
        {"language": "es", "text": "¡Soy Monkey D. Luffy y voy a ser el rey de los piratas!"},
        {"language": "hi", "text": "मैं बंदर डी. लफी हूं और मैं समुद्री डाकुओं का राजा बनने जा रहा हूं!"},
        {"language": "zh-Hans", "text": "我是 Monkey D. Luffy，我要成为海贼之王！"},
        {"language": "pl", "text": "Nazywam się Monkey D. Luffy i zamierzam zostać królem piratów!"}]}
        self.assertDictEqual(actual_result,expected_result)

    #@unittest.skip
    def test_nonexistent_player(self):
        # Send a invalid prompt request with non-existent player
        text = "I'm Monkey D. Luffy and I'm going to be king of the pirates!"
        request = { "text": text, "username": "potato"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        # Check if it detects the players not in the database
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Player does not exist')

    #@unittest.skip
    def test_Invalid_text_too_short(self):
        # Send a invalid prompt request with non-existent player
        text = "I'm Monkey D. Luffy"
        request = { "text": text, "username": "antoni_gn"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        # Check if the text is too short
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Prompt less than 20 characters or more than 100 characters')


    #@unittest.skip
    def test_Invalid_text_too_long(self):
        # Send a invalid prompt request with non-existent player
        text = "I'm Monkey D. Luffy and I'm going to be king of the pirates! And you are going to be my crewmate dude"
        request = { "text": text, "username": "antoni_gn"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        # Check if the text is too short
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Prompt less than 20 characters or more than 100 characters')

    #@unittest.skip
    def test_unsupported_language(self):
        # Send a invalid prompt request with non-existent player
        text = "海賊王におれはなる海賊王におれはなる海賊王におれはなる海賊王におれはなる"
        request = { "text": text, "username": "antoni_gn"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        # Check if it detects a language not supported
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Unsupported language')


    def test_bad_confidence_score(self):
        # Send a invalid prompt request with text that gives confidence score 0
        text = "1234"
        request = { "text": text, "username": "antoni_gn"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json()  

        # Check if it detects a language not supported
        self.assertFalse(dict_response['result'])
        self.assertEqual(dict_response['msg'],'Unsupported language')