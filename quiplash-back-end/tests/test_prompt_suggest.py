import unittest
import requests
import json
from shared_code.open_ai import open_ai

class test_prompt_suggest(unittest.TestCase):
    """
    This test set focuses on testing the responses from the server on the UtilsSuggest function.
    """

    # URLS to test on
    LOCAL_DEV_URL = "http://localhost:7071/prompt/suggest"
    PUBLIC_URL = "https://quiplash-ag7g22.azurewebsites.net/prompt/suggest"
    TEST_URL = PUBLIC_URL

    # Configure the Proxy objects from the local.settings.json file.
    with open('local.settings.json') as settings_file:
        settings = json.load(settings_file)
    FUNCTION_KEY = settings['Values']['FunctionAppKey']

    # Access to the OPENAI chatbot.
    openAiBot = open_ai() 

    # SetUp method executed before each test       
    def setUp(self):
        pass

    # tearDown method executed before each test
    # @unittest.skip
    def tearDown(self) -> None:
        pass

    # @unittest.skip
    def test_OpenAI_response(self):
        # Send a valid suggestion
        request = {"keyword": "relationship"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json() 

        # Check if you got the response with the keyword inside.
        self.assertRegex(dict_response['suggestion'],'relationship')
        # Check if the response is in the character range 20-100
        self.assertGreaterEqual(len(dict_response['suggestion']),20)
        self.assertLessEqual(len(dict_response['suggestion']),100)


    # Hard to find a keyword for getting a wrong error, from the prompt given.
    @unittest.skip
    def test_bad_response(self):
        # Send an invalid suggestion
        request = {"keyword": "coding"}
        response = requests.post(self.TEST_URL,params={"code": self.FUNCTION_KEY},json=request)

        # Get json response, check the response code for brevity
        self.assertEqual(200,response.status_code)
        dict_response = response.json() 

        # Check if you got the response with the keyword inside.
        self.assertRegex(dict_response['suggestion'],'Cannot generate suggestion')