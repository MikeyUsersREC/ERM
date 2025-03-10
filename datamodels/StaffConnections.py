import typing

from bson import ObjectId
from utils.mongo import Document
from utils.basedataclass import BaseDataClass


class StaffConnection(BaseDataClass):
    roblox_id: int
    discord_id: int
    document_id: ObjectId

    def to_document(self) -> dict:
        return (
            {"discord_id": self.discord_id, "roblox_id": self.roblox_id}
            if not self.document_id
            else {
                "_id": self.document_id,
                "discord_id": self.discord_id,
                "roblox_id": self.roblox_id,
            }
        )


class StaffConnections(Document):
    async def fetch_by_spec(
        self,
        roblox_id: typing.Optional[int] = None,
        discord_id: typing.Optional[int] = None,
        document_id: typing.Optional[typing.Union[ObjectId, str]] = None,
    ) -> StaffConnection | None:

        attributes = {}

        for key, value in {
            "roblox_id": roblox_id,
            "discord_id": discord_id,
            "_id": document_id,
        }.items():
            if value is not None:
                attributes.__setitem__(key, value)

        document = await self.db.find_one(attributes)
        if not document:
            return None

        return StaffConnection(
            roblox_id=document["roblox_id"],
            discord_id=document["discord_id"],
            document_id=document["_id"],
        )

    async def insert_connection(self, connection: StaffConnection):
        return await self.db.insert_one(connection.to_document())
