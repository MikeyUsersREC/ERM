import asyncio
import datetime
import typing

import discord
import roblox
from discord.ext import commands
import aiohttp
from decouple import config
from utils.utils import BaseDataClass
from datamodels.ServerKeys import ServerKey

class ResponseFailure(Exception):
    detail: str | None
    status_code: int
    json_data: str

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class CommandLog(BaseDataClass):
    username: str
    id: int
    timestamp: int
    is_automated: bool
    command: str

class KillLog(BaseDataClass):
    killer_username: str
    killer_user_id: int
    timestamp: int
    killed_username: str
    killed_user_id: int

class Player(BaseDataClass):
    username: str
    id: int
    permission: str


class ServerStatus(BaseDataClass):
    name: str
    owner_id: int
    co_owner_ids: list[int]
    current_players: int
    max_players: int
    join_key: str
    account_verified_request: bool
    team_balance: bool


class PRCApiClient:
    def __init__(self, bot, base_url: str, api_key: str):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.api_key = api_key
        self.base_url = base_url

        bot.external_http_sessions.append(self.session)


    async def get_server_key(self, guild_id: int) -> ServerKey:
        # TODO: code server key retrieval
        return await self.bot.server_keys.get_server_key(guild_id)
        pass

    async def _send_api_request(self, method: typing.Literal['GET', 'POST'], endpoint: str, guild_id: int, data: dict | None = None):
        internal_server_object = await self.get_server_key(guild_id)
        internal_server_key = internal_server_object.key
        async with self.session.request(method, url=f"{self.base_url}{endpoint}", headers={
            "Authorization": self.api_key,
            "Server-Key": internal_server_key
        }, json=data or {}) as response:
            return response.status, (await response.json() if response.content_type != "text/plain" else {})


    async def get_server_status(self, guild_id: int):
        status_code, response_json = await self._send_api_request('GET', '/server', guild_id)
        if status_code == 200:
            return ServerStatus(
                name=response_json['Name'],
                owner_id=response_json['OwnerId'],
                co_owner_ids=response_json['CoOwnerIds'],
                current_players=response_json['CurrentPlayers'],
                max_players=response_json['MaxPlayers'],
                join_key=response_json['JoinKey'],
                account_verified_request=response_json['AccVerifiedReq'] == 'Enabled',
                team_balance=response_json['TeamBalance']
            )
        else:
            raise ResponseFailure(
                status_code=status_code,
                json_data=response_json
            )

    async def get_server_players(self, guild_id: int) -> list:
        status_code, response_json = await self._send_api_request('GET', '/server/players', guild_id)
        if status_code == 200:
            new_list = []
            for item in response_json:
                print(item)
                new_list.append(Player(
                    username=item['Player'].split(':')[0],
                    id=item['Player'].split(':')[1],
                    permission=item['Permission']
                ))
            return new_list
        else:
            raise ResponseFailure(
                status_code=status_code,
                json_data=response_json
            )

    async def get_server_queue(self, guild_id: int) -> list:
        status_code, response_json = await self._send_api_request('GET', '/server/queue', guild_id)
        if status_code == 200:
            new_list = []
            print(response_json)
            for item in response_json:
                new_list.append(Player(
                    username=(await (roblox.Client()).get_user_by_username(item['Player'])).name,
                    id=item['Player'],
                    permission=item['Permission']
                ))
            return new_list
        else:
            raise ResponseFailure(
                status_code=status_code,
                json_data=response_json
            )

    async def fetch_server_logs(self, guild_id: int):
        status_code, response_json = await self._send_api_request('GET', '/server/commandlogs', guild_id)
        if status_code == 200:
            return [CommandLog(
                username=log_item['Player'].split(':')[0] if ':' in log_item['Player'] else log_item['Player'],
                id=log_item['Player'].split(':')[1] if ':' in log_item['Player'] else 0,
                timestamp=log_item['Timestamp'],
                is_automated=log_item['Player'] == "Remote Server",
                command=log_item['Command']
            ) for log_item in response_json]
        else:
            raise ResponseFailure(
                status_code=status_code,
                json_data=response_json
            )

    async def fetch_kill_logs(self, guild_id: int):
        status_code, response_json = await self._send_api_request('GET', '/server/killlogs', guild_id)
        if status_code == 200:
            return [KillLog(
                killer_username=log_item['Killer'].split(':')[0],
                killer_user_id=log_item['Killer'].split(':')[1],
                timestamp=log_item['Timestamp'],
                killed_username=log_item['Killed'].split(':')[0],
                killed_user_id=log_item['Killed'].split(':')[1]
            ) for log_item in response_json]
        else:
            raise ResponseFailure(
                status_code=status_code,
                json_data=response_json
            )


    async def run_command(self, guild_id: int, command: str):
        status_code, response_json = await self._send_api_request('POST', '/server/command', guild_id, data={
            "command": command
        })
        return status_code, response_json


# TODO: Testing code, remove in production
# client = PRCApiClient(None, config("PRC_API_URL"), config("PRC_API_KEY"))
# async def main():
#     server_status = await client.get_server_status(0)
#     print(f'There are currently {server_status.current_players}/{server_status.max_players} players in {server_status.join_key}.')
#     players = await client.get_server_players(0)
#     print(f'There are {len(players)} players in server.')
#     for player in players:
#         print(f'- {player.username} ({player.id})\n- {player.permission}')
#     queue = await client.get_server_queue(0)
#     print(f'There are {len(queue)} players in queue.')
#     print(queue)
#
#     # await client.run_command(0, '')
#     logs = (await client.fetch_server_logs(0))
#     for log in logs:
#         print(f"{datetime.datetime.fromtimestamp(log.timestamp).strftime('%m/%d/%Y, %H:%M:%S')} | {log.username}: {log.command}")
#
#
# asyncio.run(main())




