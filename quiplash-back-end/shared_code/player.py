import uuid
from azure.cosmos import ContainerProxy
from shared_code.utils import utils

class UniquePlayerError(ValueError):
    pass
class InvalidPlayerError(ValueError):
    pass
class InvalidPasswordError(ValueError):
    pass
class player():
    """
    Holds the information of a single player.
    """
    utility = utils()

    # Constructor with default values to faciliate player creation:
    def __init__(self,player_proxy: ContainerProxy,username="guest",password="password",games_played=0,total_score=0):
        # auto generated unique id
        self.id = str(uuid.uuid4())
        self.PlayerContainerProxy = player_proxy
        self.username = username
        self.password = password
        self.games_played = games_played
        self.total_score = total_score


    def is_valid(self):
        """
        Validation method to check the player inputted is correct.
        """
        if not self.is_unique():
            raise UniquePlayerError("Username already exists")
        
        elif not (5 <= len(self.username) <= 15):
            raise InvalidPlayerError("Username less than 5 characters or more than 15 characters")
        
        elif not (8 <= len(self.password) <= 15):
            raise InvalidPasswordError("Password less than 8 characters or more than 15 characters")
        
        return True


    def is_unique(self):
        """
        Iterates over list of players to check if it's unique
        """
        # Check if there is a player username already stored
        username = self.username
        query = 'SELECT * FROM player WHERE CONTAINS(player.username, "{}")'.format(username)
        existing_username = self.utility.get_queryed_items(proxy=self.PlayerContainerProxy,query=query)
        if not existing_username:
            # If no existing username, then its unique.
            return True
        else:
            # If there is, username already taken.
            return False


    def to_dict(self):
        """
        Function return player info as a dictionary.
        """
        dict_representation = {'id': self.id, 'username': self.username, 'password': self.password, 'games_played': self.games_played, 'total_score': self.total_score}
        return dict_representation