from azure.cosmos import ContainerProxy

class ResponseError(ValueError):
    pass
class open_ai():
    """
    Class to handle the open AI operations.
    """
    
    def suggest_prompt(self, ai_proxy: ContainerProxy, keyword):
        """
        Uses the chat playground to get the ai repsonse.
        """

        chat_completion = ai_proxy.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Give a funny prompt between 20 and 100 characters with the exact keyword {} at least once for players to answer!".format(keyword)
                }
            ],
            model="gpt-3.5-turbo-0301"
        )

        reply = chat_completion.choices[0].message.content

        # Validate reply to compensate for non-deterministic results
        if keyword not in reply:
            raise ResponseError("Cannot generate suggestion")
        else:
            return reply