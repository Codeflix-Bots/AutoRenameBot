import motor.motor_asyncio
from config import Config
from .utils import send_log

class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.madflixbotz = self._client[database_name]
        self.col = self.madflixbotz.user

    def new_user(self, id):
        return dict(
            _id=int(id),                                   
            file_id=None,
            caption=None,
            format_template=None  # Add this line for the format template
        )

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id)
            await self.col.insert_one(user)            
            await send_log(b, u)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        all_users = self.col.find({})
        return all_users

    async def delete_user(self, user_id):
        await self.col.delete_many({'_id': int(user_id)})
    
    async def set_thumbnail(self, id, file_id):
        await self.col.update_one({'_id': int(id)}, {'$set': {'file_id': file_id}})

    async def get_thumbnail(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('file_id', None)

    async def set_caption(self, id, caption):
        await self.col.update_one({'_id': int(id)}, {'$set': {'caption': caption}})

    async def get_caption(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('caption', None)

    async def set_format_template(self, id, format_template):
        await self.col.update_one({'_id': int(id)}, {'$set': {'format_template': format_template}})

    async def get_format_template(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('format_template', None)
        
    async def set_media_preference(self, id, media_type):
        await self.col.update_one({'_id': int(id)}, {'$set': {'media_type': media_type}})
        
    async def get_media_preference(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('media_type', None)

async def set_metadata(self, id, bool_meta):
        await self.col.update_one({'_id': int(id)}, {'$set': {'metadata': bool_meta}})

    async def get_metadata(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('metadata', None)

    async def set_metadata_code(self, id, metadata_code):
        await self.col.update_one({'_id': int(id)}, {'$set': {'metadata_code': metadata_code}})

    async def get_metadata_code(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('metadata_code', None)

    async def set_title(self, id, title):
        await self.col.update_one({'_id': int(id)}, {'$set': {'title': title}})

    async def get_title(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('title', None)

    async def set_author(self, id, author):
        await self.col.update_one({'_id': int(id)}, {'$set': {'author': author}})

    async def get_author(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('author', None)

    async def set_artist(self, id, artist):
        await self.col.update_one({'_id': int(id)}, {'$set': {'artist': artist}})

    async def get_artist(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('artist', None)

    async def set_audio(self, id, audio_title):
        await self.col.update_one({'_id': int(id)}, {'$set': {'audio_title': audio_title}})

    async def get_audio(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('audio_title', None)

    async def set_subtitle(self, id, subtitle):
        await self.col.update_one({'_id': int(id)}, {'$set': {'subtitle': subtitle}})

    async def get_subtitle(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('subtitle', None)

    async def set_video(self, id, video_title):
        await self.col.update_one({'_id': int(id)}, {'$set': {'video_title': video_title}})

    async def get_video(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return user.get('video_title', None)


codeflixbots = Database(Config.DB_URL, Config.DB_NAME)
        
