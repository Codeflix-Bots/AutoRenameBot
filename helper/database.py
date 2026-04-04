import motor.motor_asyncio, datetime, pytz
from config import Config
import logging  # Added for logging errors and important information
from .utils import send_log


class Database:
    def __init__(self, uri, database_name):
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self._client.server_info()  # This will raise an exception if the connection fails
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise e  # Re-raise the exception after logging it
        self.codeflixbots = self._client[database_name]
        self.col = self.codeflixbots.user

    def new_user(self, id):
        return dict(
            _id=int(id),
            join_date=datetime.date.today().isoformat(),
            file_id=None,
            caption=None,
            metadata=True,
            metadata_code="Telegram : @CartoonAndAnime1Telugu",
            format_template=None,
            token_expiry=0,
            plan="Free",
            used_renames=0,
            used_extracts=0,
            extra_extracts=0,
            usage_date=datetime.date.today().isoformat(),
            extract_language="off",
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=datetime.date.max.isoformat(),
                ban_reason=''
            )
        )

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id)
            try:
                await self.col.insert_one(user)
                await send_log(b, u)
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")

    async def is_user_exist(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await self.col.count_documents({})
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(self):
        try:
            all_users = self.col.find({})
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def delete_user(self, user_id):
        try:
            await self.col.delete_many({"_id": int(user_id)})
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")

    async def set_thumbnail(self, id, file_id):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"file_id": file_id}})
        except Exception as e:
            logging.error(f"Error setting thumbnail for user {id}: {e}")

    async def get_thumbnail(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("file_id", None) if user else None
        except Exception as e:
            logging.error(f"Error getting thumbnail for user {id}: {e}")
            return None

    async def set_caption(self, id, caption):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"caption": caption}})
        except Exception as e:
            logging.error(f"Error setting caption for user {id}: {e}")

    async def get_caption(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("caption", None) if user else None
        except Exception as e:
            logging.error(f"Error getting caption for user {id}: {e}")
            return None

    async def set_format_template(self, id, format_template):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"format_template": format_template}}
            )
        except Exception as e:
            logging.error(f"Error setting format template for user {id}: {e}")

    async def get_format_template(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("format_template", None) if user else None
        except Exception as e:
            logging.error(f"Error getting format template for user {id}: {e}")
            return None

    async def set_media_preference(self, id, media_type):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"media_type": media_type}}
            )
        except Exception as e:
            logging.error(f"Error setting media preference for user {id}: {e}")

    async def get_media_preference(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("media_type", None) if user else None
        except Exception as e:
            logging.error(f"Error getting media preference for user {id}: {e}")
            return None

    async def get_metadata(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('metadata', "Off")

    async def set_metadata(self, user_id, metadata):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'metadata': metadata}})

    async def get_title(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('title', 'Encoded by @Animes_Cruise')

    async def set_title(self, user_id, title):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'title': title}})

    async def get_author(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('author', '@Animes_Cruise')

    async def set_author(self, user_id, author):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'author': author}})

    async def get_artist(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('artist', '@Animes_Cruise')

    async def set_artist(self, user_id, artist):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'artist': artist}})

    async def get_audio(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('audio', 'By @Animes_Cruise')

    async def set_audio(self, user_id, audio):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'audio': audio}})

    async def get_subtitle(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('subtitle', "By @Animes_Cruise")

    async def set_subtitle(self, user_id, subtitle):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'subtitle': subtitle}})

    async def get_video(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('video', 'Encoded By @Animes_Cruise')

    async def set_video(self, user_id, video):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'video': video}})

    async def get_prefix(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("prefix", "[@CartoonandAnime1Telugu] ") if user else "[@CartoonandAnime1Telugu] "
        except Exception as e:
            logging.error(f"Error getting prefix for user {id}: {e}")
            return "[@CartoonandAnime1Telugu] "

    async def set_prefix(self, id, prefix):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"prefix": prefix}})
        except Exception as e:
            logging.error(f"Error setting prefix for user {id}: {e}")

    async def get_suffix(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("suffix", "") if user else ""
        except Exception as e:
            logging.error(f"Error getting suffix for user {id}: {e}")
            return ""

    async def set_suffix(self, id, suffix):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"suffix": suffix}})
        except Exception as e:
            logging.error(f"Error setting suffix for user {id}: {e}")

    async def get_telugu_only(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("telugu_only", False) if user else False
        except Exception as e:
            logging.error(f"Error getting telugu_only for user {id}: {e}")
            return False

    async def set_telugu_only(self, id, telugu_only):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"telugu_only": telugu_only}})
        except Exception as e:
            logging.error(f"Error setting telugu_only for user {id}: {e}")

    async def get_token_expiry(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("token_expiry", 0) if user else 0
        except Exception as e:
            logging.error(f"Error getting token expiry for user {id}: {e}")
            return 0

    async def set_token_expiry(self, id, expiry_time):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"token_expiry": expiry_time}})
        except Exception as e:
            logging.error(f"Error setting token expiry for user {id}: {e}")

    async def set_user_plan(self, id, plan_name):
        try:
            await self.col.update_one(
                {"_id": int(id)},
                {"$set": {
                    "plan": plan_name,
                    "used_renames": 0,
                    "used_extracts": 0,
                    "extra_extracts": 0,
                    "usage_date": datetime.date.today().isoformat()
                }}
            )
        except Exception as e:
            logging.error(f"Error setting plan for user {id}: {e}")

    async def get_plan_details(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            if not user:
                return None

            # Reset daily limits if the date has changed
            today = datetime.date.today().isoformat()
            if user.get("usage_date") != today:
                await self.col.update_one(
                    {"_id": int(id)},
                    {"$set": {
                        "usage_date": today,
                        "used_renames": 0,
                        "used_extracts": 0,
                        "extra_extracts": 0
                    }}
                )
                user["used_renames"] = 0
                user["used_extracts"] = 0
                user["extra_extracts"] = 0

            return {
                "plan": user.get("plan", "Free"),
                "used_renames": user.get("used_renames", 0),
                "used_extracts": user.get("used_extracts", 0),
                "extra_extracts": user.get("extra_extracts", 0)
            }
        except Exception as e:
            logging.error(f"Error getting plan details for user {id}: {e}")
            return None

    async def update_usage(self, id, field, increment=1):
        try:
            await self.col.update_one({"_id": int(id)}, {"$inc": {field: increment}})
        except Exception as e:
            logging.error(f"Error updating usage {field} for user {id}: {e}")

    async def get_extract_language(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("extract_language", "off") if user else "off"
        except Exception as e:
            logging.error(f"Error getting extract_language for user {id}: {e}")
            return "off"

    async def set_extract_language(self, id, language):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"extract_language": language.lower()}})
        except Exception as e:
            logging.error(f"Error setting extract_language for user {id}: {e}")


codeflixbots = Database(Config.DB_URL, Config.DB_NAME)
