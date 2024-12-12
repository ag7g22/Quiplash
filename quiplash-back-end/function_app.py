import os
import json
import logging
import azure.functions as func
from azure.cosmos import CosmosClient
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# shared_code folder helper functions and classes
from shared_code.player import player, UniquePlayerError, InvalidPlayerError, InvalidPasswordError
from shared_code.prompt import prompt, UnsupportedLanguageError, InvalidTextError, NonExistingPlayerError
from shared_code.open_ai import open_ai, ResponseError
from shared_code.utils import utils

app = func.FunctionApp()

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])     # Cosmos Object
QuiplashProxy = MyCosmos.get_database_client(os.environ['DatabaseName'])                        # Proxy for quiplash database
PlayerContainerProxy = QuiplashProxy.get_container_client(os.environ['PlayerContainerName'])    # Proxy for player container
PromptContainerProxy = QuiplashProxy.get_container_client(os.environ['PromptContainerName'])    # Proxy for prompt container
TranslatorProxy = TextTranslationClient(endpoint=os.environ['TranslationEndpoint'], 
                                        credential=AzureKeyCredential(os.environ['TranslationKey'])) # Proxy for translator
OpenAIProxy = AzureOpenAI(api_key=os.environ['OAIKey'], api_version="2024-02-01", # Proxy for Open_AI
                        azure_endpoint=os.environ['OAIEndpoint'],
                        azure_deployment="gpt-35-turbo"
                        )

utility = utils()
oai = open_ai()


# Cosmos decorator for registering a new player.
@app.cosmos_db_output(  arg_name="playercontainerbinding",
        	            database_name=os.environ['DatabaseName'],
                        container_name=os.environ['PlayerContainerName'],
                        create_if_not_exists=True,
                        connection='AzureCosmosDBConnectionString')
@app.route(route="player/register", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def player_register(req: func.HttpRequest, playercontainerbinding: func.Out[func.Document]) -> func.HttpResponse:
    """
    Recieves a player's username and password in a JSON string to register to player container.
    e.g. {"username":  "antoni_gn" , "password" : "ILoveTricia"}
    """
    input = req.get_json()
    logging.info('Python HTTP trigger function processed a PLAYER_REGISTER request: {}'.format(input))

    # Converted to player object for validation.
    input_player = player(player_proxy=PlayerContainerProxy,username=input['username'], password=input['password'])
    logging.info("Inputted new player: {}".format(input_player.to_dict()))

    try:
        if input_player.is_valid():
            # Insert in DB if player successfully validated.
            player_doc_for_cosmos = func.Document.from_dict(input_player.to_dict())
            playercontainerbinding.set(player_doc_for_cosmos)
            logging.info("SUCCESS: Input player is valid, out binding successfully set.")
            return func.HttpResponse(body=json.dumps({"result": True, "msg": "OK"}),mimetype="application/json")

    # Send error messages based on is_valid()'s result.
    except UniquePlayerError as e:
        logging.info("FAILURE: {}".format(e))
        response_body = json.dumps({"result": False, "msg": "Username already exists"})
        return func.HttpResponse(body=response_body,mimetype="application/json")
    
    except InvalidPlayerError as e:
        logging.info("FAILURE: {}".format(e))
        response_body = json.dumps({"result": False, "msg": "Username less than 5 characters or more than 15 characters"})
        return func.HttpResponse(body=response_body,mimetype="application/json")
    
    except InvalidPasswordError as e:
        logging.info("FAILURE: {}".format(e))
        response_body = json.dumps({"result": False, "msg": "Password less than 8 characters or more than 15 characters"})
        return func.HttpResponse(body=response_body,mimetype="application/json")



@app.route(route="player/login", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)
def player_login(req: func.HttpRequest) -> func.HttpResponse:
    """
    Recieves a login attempt in a JSON document and checks credentials in the DB.
    e.g. {"username":  "antoni_gn" , "password" : "ILoveTricia"}
    """
    input = req.get_json()
    logging.info('Python HTTP trigger function processed a PLAYER_LOGIN request: {}'.format(input))

    # Extract the details from the inputted JSON.
    username = input['username']
    password = input['password']

    # Search for the player's credentials in the database.
    query = 'SELECT * FROM player WHERE CONTAINS(player.username, "{0}") AND player.password = "{1}"'.format(username, password)
    players = utility.get_queryed_items(PlayerContainerProxy,query=query)
    if players:
        logging.info("SUCCESS: login credentials validated.")
        response_body = json.dumps({"result": True, "msg": "OK"})
        return func.HttpResponse(body=response_body,mimetype="application/json")
    else:
        logging.info("FAILURE: Username or password incorrect")
        response_body = json.dumps({"result": False, "msg": "Username or password incorrect"})
        return func.HttpResponse(body=response_body,mimetype="application/json")



@app.route(route="player/update/", methods=[func.HttpMethod.PUT], auth_level=func.AuthLevel.FUNCTION)
def player_update(req: func.HttpRequest) -> func.HttpResponse:
    """
    Recieves a update request in a JSON document, updates queried player.
    e.g. {"username": "user_to_modify" , "add_to_games_played": int , "add_to_score" : int } 
    adds "add_to_games_played" to player's "games_played" and "add_to_score" to player's total_score.
    """
    input = req.get_json()
    logging.info('Python HTTP trigger function processed an PLAYER_UPDATE request: {}'.format(input))

    # Extract the input parameters
    username = input['username']
    add_to_games_played = input['add_to_games_played']
    add_to_score = input['add_to_score']

    # Search for the player's credentials in the database
    query = 'SELECT * FROM player WHERE CONTAINS(player.username, "{0}")'.format(username)
    query_result = utility.get_queryed_items(proxy=PlayerContainerProxy,query=query)
    if query_result:
        # Retrieve player item
        id = [item['id'] for item in query_result][0]
        logging.info('id found: {}'.format(id))        

        update = utility.update_player(proxy=PlayerContainerProxy,id=id,games=add_to_games_played,score=add_to_score)
        logging.info("Player's updated values -> games_played: {0}, total_score: {1}".format(update[0], update[1]))

        # Send response
        logging.info("SUCCESS: Player update executed successfully.")
        response_body = json.dumps({"result": True, "msg": "OK"})
        return func.HttpResponse(body=response_body,mimetype="application/json")
    else:
        # Non-existent player
        logging.info("FAILURE: Player does not exist")
        response_body = json.dumps({"result": False, "msg": "Player does not exist" })
        return func.HttpResponse(body=response_body,mimetype="application/json")



# Cosmos decorator for registering a new prompt.
@app.cosmos_db_output(  arg_name="promptcontainerbinding",
        	            database_name=os.environ['DatabaseName'],
                        container_name=os.environ['PromptContainerName'],
                        create_if_not_exists=True,
                        connection='AzureCosmosDBConnectionString')
@app.route(route="prompt/create", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def prompt_create(req: func.HttpRequest, promptcontainerbinding: func.Out[func.Document]) -> func.HttpResponse:
    """
    Recieves a create prompt request in a JSON document.
    e.g. {"text": "string", "username": "string" }
    """
    input = req.get_json()
    logging.info('Python HTTP trigger function processed an PROMPT_CREATE request: {}'.format(input))

    # Get the parameters in the prompt object.
    input_prompt = prompt(PlayerContainerProxy,TranslatorProxy,text=input['text'], username=input['username'])
    logging.info(input_prompt.to_dict())

    try:
        if input_prompt.is_valid():
            # Insert in DB if prompt successfully validated. 
            prompt_doc_for_cosmos = func.Document.from_dict(input_prompt.to_dict())
            promptcontainerbinding.set(prompt_doc_for_cosmos)
            logging.info("SUCCESS: Input prompt is valid, out binding successfully set.")
            return func.HttpResponse(body=json.dumps({"result": True, "msg": "OK"}),mimetype="application/json")

    # Send error messages based on is_valid()'s result. 
    except NonExistingPlayerError as e:
        logging.info("FAILURE: {}".format(e))
        response_body = json.dumps({"result": False, "msg": "Player does not exist" })
        return func.HttpResponse(body=response_body,mimetype="application/json")

    except InvalidTextError as e:
        logging.info("FAILURE: {}".format(e))
        response_body = json.dumps({"result": False, "msg": "Prompt less than 20 characters or more than 100 characters" })
        return func.HttpResponse(body=response_body,mimetype="application/json")

    except UnsupportedLanguageError as e:
        logging.info("FAILURE: {}".format(e))
        response_body = json.dumps({"result": False, "msg": "Unsupported language" })
        return func.HttpResponse(body=response_body,mimetype="application/json")



@app.route(route="prompt/suggest", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def prompt_suggest(req: func.HttpRequest) -> func.HttpResponse:
    """
    Recieves a create prompt request in a JSON document, and returns the ai-bots response.
    e.g. {"keyword": "string" }
    """
    input = req.get_json()
    logging.info('Python HTTP trigger function processed a PROMPT_SUGGEST request: {}'.format(input))
    
    # Get keyword and input it in the ai bot.
    keyword = input['keyword']

    try:
        suggestion = oai.suggest_prompt(ai_proxy=OpenAIProxy,keyword=keyword)
        if suggestion:
            # Send the resulted suggestion.
            logging.info("SUCCESS: generated the following suggestion -> {}".format(suggestion))
            return func.HttpResponse(body=json.dumps({"suggestion": suggestion}),mimetype="application/json")
    except ResponseError as e:
        # If it gives an invalid response.
        logging.info("FAILURE: {}".format(e))
        response_body = json.dumps({"suggestion" : "Cannot generate suggestion" })
        return func.HttpResponse(body=response_body,mimetype="application/json")



@app.route(route="prompt/delete", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION)
def prompt_delete(req: func.HttpRequest) -> func.HttpResponse:
    """
    Recieves a delete prompt request in a JSON document and deletes all prompts authored by player "username"
    e.g. {"player" : "username" } 
    """
    input = req.get_json()
    logging.info('Python HTTP trigger function processed a PROMPT_DELETE request: {}'.format(input))

    # query all the prompts from inputted player
    username = input['player']
    query = "SELECT * FROM prompt WHERE prompt.username = '{}'".format(username)
    query_result = utility.get_queryed_items(PromptContainerProxy, query=query)
    count = len(query_result)
    
    # Delete all the matched items
    for item in query_result:
        PromptContainerProxy.delete_item(item=item,partition_key=username)
    message = "{} prompts deleted".format(str(count))

    logging.info("SUCCESS: {}".format(message))
    return func.HttpResponse(body=json.dumps({"result": True, "msg": message}),mimetype="application/json")



@app.route(route="utils/get", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)
def utils_get(req: func.HttpRequest) -> func.HttpResponse:
    """
    {"players":  [list of usernames], "language": "langcode"} return a list of all prompts' texts in "langcode" language created by the players in the "players" list. 
    If a player in "players" does not exist or does not have any prompt , do not return error, return prompts from users that do exist and have prompts.
    If none of the usernames in the list exist or have prompts, return an empty list. 
    Output can be in any order.
    You may assume we will not test an invalid "langcode"
    """
    input = req.get_json()
    logging.info('Python HTTP trigger function processed a UTILS_GET request: {}'.format(input))

    # query the list of users and the language
    usernames = input['players']
    language = input['language']

    # Write the SQL to get the given users' prompts in the given language
    usernames_for_SQL = utility.convert_to_query_list(usernames)
    query = "SELECT p.id, t.text, p.username FROM prompt p JOIN t IN p.texts WHERE t.language = '{0}' AND p.username IN {1}".format(language,usernames_for_SQL)
    query_result = utility.get_queryed_items(PromptContainerProxy, query=query)

    # Append the results in the appropriate format
    dict_result = []
    for item in query_result:
        dict_result.append({ "id": item['id'], "text": item['text'], "username": item['username'] })

    logging.info("Sending the result: {}".format(dict_result))
    return func.HttpResponse(body=json.dumps(dict_result),mimetype="application/json")



@app.route(route="utils/podium", methods=[func.HttpMethod.GET], auth_level=func.AuthLevel.FUNCTION)
def utils_podium(req: func.HttpRequest) -> func.HttpResponse:
    """
    Output the dictionary of list of players with the highest ppgr (points per game ratio)
    Note two or more players may have the same points per game ratio, which is why we ask for a dict of lists. 
    In case of multiple players with same ppgr, the list must be ordered by increasing number of games played, then by increasing alphabetic order.
    """
    logging.info('Python HTTP trigger function processed a UTILS_PODIUM request')
    # Query for the list of players
    query = "SELECT p.username, p.games_played, p.total_score FROM player p"
    query_result = utility.get_queryed_items(PlayerContainerProxy, query=query)

    # Orders the players in ranking order and present in podium.
    players_ranked = utility.sort_to_ppgr_games_played(query_result)
    podium = utility.get_podium(players_ranked)

    logging.info("FINAL PODIUM: {}".format(podium))
    return func.HttpResponse(body=json.dumps(podium),mimetype="application/json")