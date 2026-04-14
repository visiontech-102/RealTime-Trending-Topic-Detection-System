import asyncio
from database.connection import get_database

async def clean_mock_data():
    db = await get_database()
    tweets_collection = db["raw_tweets"]

    # Mock text patterns to identify and remove
    mock_patterns = [
        "The stock market saw a massive increase",
        "Climate change discussions dominate",
        "A new deep learning model has been open-sourced",
        "SpaceX successfully launched another mission",
        "Qarax xoogan ayaa maanta ka dhacay",
        "Doorashada madaxweynaha ayaa la filayaa",
        "Banaanbax nabadeed ayaa ka dhacay",
        "Abaarta ka jirta gobolada qaar",
        "Ganacsiga Soomaaliya ayaa horumar"
    ]

    # Build regex pattern to match any mock tweet
    pattern = "|".join(mock_patterns)
    query = {"text": {"$regex": pattern, "$options": "i"}}

    # Count mock tweets
    mock_count = await tweets_collection.count_documents(query)
    print(f"Found {mock_count} mock tweets to remove.")

    if mock_count > 0:
        # Delete mock tweets
        result = await tweets_collection.delete_many(query)
        print(f"Removed {result.deleted_count} mock tweets.")

    # Count remaining tweets (should be real)
    remaining_count = await tweets_collection.count_documents({})
    print(f"Remaining tweets: {remaining_count}")

    # Show a few remaining tweets to verify they are real
    if remaining_count > 0:
        cursor = tweets_collection.find().sort("timestamp", -1).limit(3)
        remaining_tweets = await cursor.to_list(length=3)
        print("\nSample remaining tweets:")
        for tweet in remaining_tweets:
            print(f"  {tweet.get('language', 'unknown')}: {tweet.get('text', '')[:60]}...")

if __name__ == "__main__":
    asyncio.run(clean_mock_data())