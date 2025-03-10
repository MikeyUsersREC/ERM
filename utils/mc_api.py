import asyncio
import typing
import aiohttp
from datamodels.ServerKeys import ServerKey
from utils.prc_api import ResponseFailure, ServerStatus, Player, CommandLog, BanItem


class MCApiClient:
    def __init__(self, bot, base_url: str, api_key: str):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.api_key = api_key
        self.base_url = base_url

        bot.external_http_sessions.append(self.session)

    async def get_server_key(self, guild_id: int) -> ServerKey:
        return await self.bot.mc_keys.get_server_key(guild_id)

    async def _send_api_request(
        self,
        method: typing.Literal["GET", "POST"],
        endpoint: str,
        guild_id: int,
        data: dict | None = None,
        key: str | None = None,
    ):
        if not key:
            internal_server_object = await self.get_server_key(guild_id)
            internal_server_key = (
                internal_server_object if internal_server_object is not None else None
            )
            if internal_server_key is None:
                return 401, {}
            else:
                internal_server_key = internal_server_key.key
        else:
            internal_server_key = key

        async with self.session.request(
            method,
            url=f"{self.base_url}{endpoint}",
            headers={
                "X-Static-Token": self.api_key,
                "Authorization": internal_server_key,
                "User-Agent": "ERM Bot (version 4)",
            },
            json=data or {},
        ) as response:
            if response.status == 429:
                retry_after = int((await response.json()).get("retry_after", 5))
                await asyncio.sleep(retry_after)
                return await self._send_api_request(
                    method=method,
                    endpoint=endpoint,
                    guild_id=guild_id,
                    data=data,
                    key=key,
                )
            if response.status == 502:
                return await self._send_api_request(
                    method=method,
                    endpoint=endpoint,
                    guild_id=guild_id,
                    data=data,
                    key=key,
                )
            return response.status, (
                await response.json() if response.content_type != "text/html" else {}
            )

    async def get_server_status(self, guild_id: int):
        status_code, response_json = await self._send_api_request(
            "GET", "/Server", guild_id
        )
        if status_code == 200:
            return ServerStatus(
                name=response_json["Name"],
                owner_id=response_json["OwnerId"],
                co_owner_ids=response_json["CoOwnerIds"],
                current_players=response_json["CurrentPlayers"],
                max_players=response_json["MaxPlayers"],
                join_key=response_json["JoinKey"],
                # account_verified_request=response_json['AccVerifiedReq'] == 'Enabled',
                # team_balance=response_json['TeamBalance']
            )
        else:
            raise ResponseFailure(status_code=status_code, json_data=response_json)

    async def send_test_request(self, server_key: str) -> int | ServerStatus:
        code, response_json = await self._send_api_request(
            "GET", "/Server", 0, None, server_key
        )
        return (
            code
            if code != 200
            else ServerStatus(
                name=response_json["Name"],
                owner_id=response_json["OwnerId"],
                co_owner_ids=response_json["CoOwnerIds"],
                current_players=response_json["CurrentPlayers"],
                max_players=response_json["MaxPlayers"],
                join_key=response_json["JoinKey"],
                # account_verified_request=response_json['AccVerifiedReq'] == 'Enabled', - noah forgot to implement this!
                # team_balance=response_json['TeamBalance']
            )
        )

    async def get_server_players(self, guild_id: int) -> list:
        status_code, response_json = await self._send_api_request(
            "GET", "/Server/Players", guild_id
        )
        if status_code == 200:
            new_list = []
            for item in response_json:
                # print(item)
                new_list.append(
                    Player(
                        username=item["Player"].split(":")[0],
                        id=item["Player"].split(":")[1],
                        permission=item["Permission"],
                        callsign=item.get("Callsign"),
                        team=item["Team"],
                    )
                )
            return new_list
        else:
            raise ResponseFailure(status_code=status_code, json_data=response_json)

    async def authorize(self, roblox_id: int, server_name: str, guild_id: int):
        status_code, response_json = await self._send_api_request(
            "POST",
            "/Server/Auth",
            0,
            {"RobloxId": roblox_id, "ServerName": server_name, "GuildId": guild_id},
            key="__PRE_AUTHORIZATION",
        )

        if status_code == 200:
            return response_json["token"]
        else:
            raise ResponseFailure(status_code=status_code, json_data=response_json)

    async def fetch_server_logs(self, guild_id: int):
        status_code, response_json = await self._send_api_request(
            "GET", "/Server/Commands", guild_id
        )
        if status_code == 200:
            return [
                CommandLog(
                    username=(
                        log_item["Player"].split(":")[0]
                        if ":" in log_item["Player"]
                        else log_item["Player"]
                    ),
                    user_id=(
                        log_item["Player"].split(":")[1]
                        if ":" in log_item["Player"]
                        else 0
                    ),
                    timestamp=log_item["Timestamp"],
                    is_automated=log_item["Player"] == "Remote Server",
                    command=log_item["Command"],
                )
                for log_item in response_json
            ]
        else:
            raise ResponseFailure(status_code=status_code, json_data=response_json)

    async def fetch_bans(self, guild_id: int):
        status_code, response_json = await self._send_api_request(
            "GET", "/Server/Bans", guild_id
        )

        if status_code == 200:
            if response_json == []:
                return []
            return [
                BanItem(user_id=int(user_id), username=username)
                for user_id, username in response_json.items()
            ]
        else:
            raise ResponseFailure(status_code=status_code, json_data=response_json)
