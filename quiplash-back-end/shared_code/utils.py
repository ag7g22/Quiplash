from typing import List, Dict, Any
from azure.cosmos import ContainerProxy

class utils():
    """
    Utility class for querying in SQL & building dictionaries.
    """

    def get_queryed_items(self, proxy: ContainerProxy, query: str):
        """
        Returns items from proxy objects' querying.
        """
        return list(proxy.query_items(query=query, enable_cross_partition_query=True))


    def update_player(self, proxy: ContainerProxy, id: str, games, score):
        """
        Updates the inputted player.
        """
        # Retrieve the player from the database.
        player_to_update = proxy.read_item(item=id,partition_key=id)
        recent_games_played = player_to_update['games_played']
        recent_total_score = player_to_update['total_score']

        # Cap negative values of games_played to zero.
        if (games < 0):
            games = 0

        # If the negative score reaches beyond 0 in the total_score, cap at 0.
        if (-score > player_to_update['total_score']):
                recent_total_score = 0
                score = 0

        # Increment the games_played and total_score
        games_played = recent_games_played + games
        total_score = recent_total_score + score

        # New Values in a dictionary
        updates = {"games_played": games_played, "total_score": total_score}

        # Modify the player via field names as keys:
        for key, value in updates.items():
            player_to_update[key] = value

        # Replace item
        proxy.replace_item(item=player_to_update['id'], body=player_to_update)

        # Return the updated games_played and total_score:
        return [ games_played, total_score ]


    def convert_to_query_list(self, players: List[str]):
        """
        Returns a list of strings to this format for SQL:
        i.e. ["a","b","c"] -> ("a","b","c")
        """
        return '("' + '", "'.join(players) + '")'
    

    def get_ppgr(self, total_score: int, games_played: int) -> int:
        """
        Calculates the pprg of a certain player
        """
        # If theres no games played pprg = 0
        if games_played == 0:
            return 0
        
        # Return floating point to 2sf
        ppgr = total_score / games_played
        return round(ppgr, 2 - int(ppgr != 0 and ppgr >= 10))


    def sort_to_ppgr_games_played(self, player_stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Returns a list of players_stats to ascending order:
        First ppgr, then less games_played, finally alphabetical order
        """
        for player in player_stats:
            player['ppgr'] = self.get_ppgr(player['total_score'],player['games_played'])

        return sorted(player_stats, key=lambda x: (-x['ppgr'], x['games_played'], x['username'].lower()))
    

    def get_podium(self, leaderboard: List[Dict[str, Any]]) -> Dict:
        """
        Gets the players off from top 3 ggpr scores
        """
        podium = {"gold": [], "silver": [], "bronze": []}
        # This tracks if the next player's ppgr is different or not
        current_ppgr = leaderboard[0]['ppgr']
        # This tracks the current entry in the podium
        ranks = ["gold", "silver", "bronze"]
        r_index = 0
        current_rank = ranks[r_index]

        for player in leaderboard:
            # If this new player has a lower ppgr than the previous player's ppgr, go down a rank
            if player['ppgr'] != current_ppgr:
                current_ppgr = player['ppgr']
                r_index = r_index + 1
                # If the index goes below bronze, stop appending
                if r_index > 2:
                    break
                else:
                   current_rank = ranks[r_index] 
            # Add player to current rank
            player.pop('ppgr', None)
            podium[current_rank].append(player)

        return podium