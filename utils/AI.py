import typing
from decouple import config
import aiohttp


class Punishment:
    def __init__(self, text, prediction, confidence, *args, **kwargs):
        self.text = text
        self.prediction = prediction
        self.confidence = confidence
        self.modified = kwargs.get("modified", False)


class AI:
    def __init__(self, api_url, api_auth):
        self.api_url = api_url
        self.api_auth = api_auth

    async def recommended_punishment(
        self, reason: str, past: typing.Union[list[str], None]
    ) -> Punishment:
        if past is None:
            past = []
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}?auth={self.api_auth}&version=1",
                json=[reason],
            ) as resp:
                result = await resp.json()
                # # # print(result)
                if not past:
                    res = result[-1]
                    return Punishment(
                        text=res["text"],
                        prediction=res["prediction"],
                        confidence=res["confidence"],
                    )

            weights = {"Warning": 1, "Kick": 3, "Ban": 4, "BOLO": 4}
            score = weights.get(result[0]["prediction"], 0) + sum(
                [weights.get(x, 0) for x in past]
            )
            # # # print(score)
            if result[-1]["prediction"] == "BOLO":
                # return "BOLO"
                return Punishment(
                    text=result[-1]["text"],
                    prediction="BOLO",
                    confidence=result[-1]["confidence"],
                    modified=True,
                )
            if score < 3:
                # return "Warning"
                return Punishment(
                    text=result[-1]["text"],
                    prediction="Warning",
                    confidence=result[-1]["confidence"],
                    modified=True,
                )
            elif (score < 4) or score <= 5 and result[-1]["prediction"] == "Kick":
                return Punishment(
                    text=result[-1]["text"],
                    prediction="Kick",
                    confidence=result[-1]["confidence"],
                    modified=True,
                )
            else:
                return Punishment(
                    text=result[-1]["text"],
                    prediction="Ban",
                    confidence=result[-1]["confidence"],
                    modified=True,
                )
