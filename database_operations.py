import uuid
import logging
from datetime import datetime

def insert_most_followed_stock(cursor, connection, name, ticker, open_price, close_price, intraday_percentage, current_price, intraday_change, seven_day_change, seven_day_percentage, volume, country, stock_exchange, stock_type):
    """
    Inserts a single record into the most_followed_stocks table in PostgreSQL 
    after deleting any existing data for the given ticker and stock_type.
    
    Parameters:
    name (str): Name of the stock.
    ticker (str): Ticker symbol of the stock.
    open_price (float): Opening price of the stock.
    close_price (float): Closing price of the stock.
    intraday_percentage (float): Intraday percentage change of the stock.
    current_price (float): Current price of the stock.
    intraday_change (float): Intraday price change of the stock.
    seven_day_change (float): Change in price over the last 7 days.
    seven_day_percentage (float): Percentage change in price over the last 7 days.
    volume (float): Volume of the stock traded.
    country (str): Country of the stock.
    stock_exchange (str): Stock exchange where the stock is listed.
    stock_type (str): Type of stock.
    """
    try:
        # Convert all necessary values to standard Python types, if necessary
        open_price = float(open_price) if open_price is not None else None
        close_price = float(close_price) if close_price is not None else None
        intraday_percentage = float(intraday_percentage) if intraday_percentage is not None else None
        current_price = float(current_price) if current_price is not None else None
        intraday_change = float(intraday_change) if intraday_change is not None else None
        seven_day_change = float(seven_day_change) if seven_day_change is not None else None
        seven_day_percentage = float(seven_day_percentage) if seven_day_percentage is not None else None
        volume = float(volume) if volume is not None else None

        # First, delete any existing records for the given ticker and stock_type
        delete_query = """
        DELETE FROM api_app_mostfollowedstocks 
        WHERE ticker = %s AND stock_type = %s;
        """
        cursor.execute(delete_query, (ticker, stock_type))

        # SQL query to insert data into the most_followed_stocks table
        insert_query = """
        INSERT INTO api_app_mostfollowedstocks (
            id, name, ticker, open_price, close_price, intraday_percentage, 
            current_price, intraday_change, seven_day_change, seven_day_percentage, 
            volume, country, stock_exchange, stock_type
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """

        # Data to be inserted (parameters passed to the function)
        stock_data = (
            str(uuid.uuid4()),  # id (UUID)
            name,               # name
            ticker,             # ticker
            open_price,         # open_price
            close_price,        # close_price
            intraday_percentage,# intraday_percentage
            current_price,      # current_price
            intraday_change,    # intraday_change
            seven_day_change,   # seven_day_change
            seven_day_percentage,# seven_day_percentage
            volume,             # volume
            country,            # country
            stock_exchange,     # stock_exchange
            stock_type          # stock_type
        )

        # Execute the SQL query with the data
        cursor.execute(insert_query, stock_data)
        
        # Commit the transaction
        connection.commit()
        print(f"Data for {ticker} inserted successfully!")

    except Exception as e:
        # Rollback the transaction in case of an error
        connection.rollback()
        print(f"Error inserting data for {ticker}: {e}")

def insert_stock_metrics(cursor, connection, stock_type, company_name, ticker, exchange, domiciled, mine_location, primary_resource, pureplay, market_cap, last_price, intraday_percentage, volume, ytd_percentage, week_52_low, week_52_high):
    """Insert stock metrics into the database"""
    try:
        # Generate UUID for the record
        record_id = str(uuid.uuid4())
        
        # First delete existing records for this ticker
        cursor.execute("DELETE FROM api_app_stockmetrics WHERE ticker = %s", (ticker,))
        
        # Insert with correct column order matching the database schema
        cursor.execute("""
        INSERT INTO api_app_stockmetrics (
            id, ticker, company_name, market_cap, volume, domiciled, exchange,
            intraday_percentage, last_price, mine_location, primary_resource,
            pureplay, stock_type, week_52_high, week_52_low, ytd_percentage,
            last_updated, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (
            record_id, ticker, company_name, market_cap, volume, domiciled, exchange,
            intraday_percentage, last_price, mine_location, primary_resource,
            pureplay, stock_type, week_52_high, week_52_low, ytd_percentage
        ))
        
        connection.commit()
        print(f"Successfully inserted/updated metrics for {ticker}")
        
    except Exception as e:
        print(f"Error inserting metrics for {ticker}: {e}")
        connection.rollback()

# ============================================================================
# PRESS RELEASE OPERATIONS
# ============================================================================



def insert_press_release(cursor, connection, press_release_data):
    """Insert a press release into the database"""
    try:
        insert_query = """
        INSERT INTO api_app_pressreleases (
            id, ticker, company_name, title, date, url, content, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO UPDATE SET
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        # Generate UUID for the record
        record_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        data = (
            record_id,
            press_release_data['ticker'],
            press_release_data['company_name'],
            press_release_data['title'],
            press_release_data['date'],
            press_release_data['url'],
            press_release_data['content'],
            current_time,
            current_time
        )
        
        cursor.execute(insert_query, data)
        connection.commit()
        
        logging.info(f"Inserted press release: {press_release_data['title'][:50]}...")
        
    except Exception as e:
        logging.error(f"Error inserting press release: {e}")
        connection.rollback()

def check_press_release_url_exists(cursor, url):
    """Check if a press release URL already exists in the database"""
    try:
        check_query = "SELECT COUNT(*) FROM api_app_pressreleases WHERE url = %s;"
        cursor.execute(check_query, (url,))
        count = cursor.fetchone()[0]
        return count > 0
        
    except Exception as e:
        logging.error(f"Error checking press release URL existence: {e}")
        return False

def get_press_releases_by_ticker(cursor, ticker, limit=10):
    """Get press releases for a specific ticker"""
    try:
        query = """
        SELECT ticker, company_name, title, date, url, content, created_at
        FROM api_app_pressreleases 
        WHERE ticker = %s 
        ORDER BY created_at DESC 
        LIMIT %s;
        """
        
        cursor.execute(query, (ticker, limit))
        results = cursor.fetchall()
        
        press_releases = []
        for row in results:
            press_releases.append({
                'ticker': row[0],
                'company_name': row[1],
                'title': row[2],
                'date': row[3],
                'url': row[4],
                'content': row[5],
                'created_at': row[6]
            })
        
        return press_releases
        
    except Exception as e:
        logging.error(f"Error getting press releases for {ticker}: {e}")
        return []

def get_recent_press_releases(cursor, limit=50):
    """Get recent press releases across all tickers"""
    try:
        query = """
        SELECT ticker, company_name, title, date, url, content, created_at
        FROM api_app_pressreleases 
        ORDER BY created_at DESC 
        LIMIT %s;
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        press_releases = []
        for row in results:
            press_releases.append({
                'ticker': row[0],
                'company_name': row[1],
                'title': row[2],
                'date': row[3],
                'url': row[4],
                'content': row[5],
                'created_at': row[6]
            })
        
        return press_releases
        
    except Exception as e:
        logging.error(f"Error getting recent press releases: {e}")
        return []

def delete_old_press_releases(cursor, connection, days_old=90):
    """Delete press releases older than specified days"""
    try:
        delete_query = """
        DELETE FROM api_app_pressreleases 
        WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days';
        """
        
        cursor.execute(delete_query, (days_old,))
        deleted_count = cursor.rowcount
        connection.commit()
        
        logging.info(f"Deleted {deleted_count} press releases older than {days_old} days")
        return deleted_count
        
    except Exception as e:
        logging.error(f"Error deleting old press releases: {e}")
        connection.rollback()
        return 0

def get_press_release_stats(cursor):
    """Get statistics about press releases in the database"""
    try:
        stats_query = """
        SELECT 
            COUNT(*) as total_press_releases,
            COUNT(DISTINCT ticker) as unique_tickers,
            MIN(created_at) as oldest_press_release,
            MAX(created_at) as newest_press_release
        FROM api_app_pressreleases;
        """
        
        cursor.execute(stats_query)
        result = cursor.fetchone()
        
        return {
            'total_press_releases': result[0],
            'unique_tickers': result[1],
            'oldest_press_release': result[2],
            'newest_press_release': result[3]
        }
        
    except Exception as e:
        logging.error(f"Error getting press release stats: {e}")
        return None

def update_process_status(cursor, connection, process_name):
    """Update the current process status"""
    cursor.execute("DELETE FROM process_python1")
    cursor.execute("INSERT INTO process_python1 (current_process) VALUES (%s)", (process_name,))
    connection.commit()

# ============================================================================
# STOCK NEWS OPERATIONS
# ============================================================================

def insert_stock_news(cursor, connection, stock_news_data):
    """Insert a stock news item into the database"""
    try:
        insert_query = """
        INSERT INTO api_app_stocknews (
            id, ticker, company_name, exchange, yahoo_ticker, title, summary, 
            date, image_url, url, provider, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO UPDATE SET
            title = EXCLUDED.title,
            summary = EXCLUDED.summary,
            date = EXCLUDED.date,
            image_url = EXCLUDED.image_url,
            provider = EXCLUDED.provider,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        # Generate UUID for the record
        record_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        # Handle None date - use current date if date is None (date field is NOT NULL in database)
        news_date = stock_news_data.get('date')
        if news_date is None:
            news_date = current_time.strftime("%Y-%m-%d")
        
        data = (
            record_id,
            stock_news_data['ticker'],
            stock_news_data['company_name'],
            stock_news_data['exchange'],
            stock_news_data['yahoo_ticker'],
            stock_news_data['title'],
            stock_news_data['summary'],
            news_date,
            stock_news_data['image'],
            stock_news_data['url'],
            stock_news_data['provider'],
            current_time,
            current_time
        )
        
        cursor.execute(insert_query, data)
        connection.commit()
        
        logging.info(f"Inserted stock news: {stock_news_data['ticker']} - {stock_news_data['title'][:50]}...")
        
    except Exception as e:
        logging.error(f"Error inserting stock news: {e}")
        connection.rollback()

def check_stock_news_url_exists(cursor, url):
    """Check if a stock news URL already exists in the database"""
    try:
        check_query = "SELECT COUNT(*) FROM api_app_stocknews WHERE url = %s;"
        cursor.execute(check_query, (url,))
        count = cursor.fetchone()[0]
        return count > 0
        
    except Exception as e:
        logging.error(f"Error checking stock news URL existence: {e}")
        return False

def get_stock_news_by_ticker(cursor, ticker, limit=10):
    """Get stock news for a specific ticker"""
    try:
        query = """
        SELECT ticker, company_name, exchange, yahoo_ticker, title, summary, 
               date, image_url, url, provider, created_at
        FROM api_app_stocknews 
        WHERE ticker = %s 
        ORDER BY created_at DESC 
        LIMIT %s;
        """
        
        cursor.execute(query, (ticker, limit))
        results = cursor.fetchall()
        
        stock_news = []
        for row in results:
            stock_news.append({
                'ticker': row[0],
                'company_name': row[1],
                'exchange': row[2],
                'yahoo_ticker': row[3],
                'title': row[4],
                'summary': row[5],
                'date': row[6],
                'image_url': row[7],
                'url': row[8],
                'provider': row[9],
                'created_at': row[10]
            })
        
        return stock_news
        
    except Exception as e:
        logging.error(f"Error getting stock news for {ticker}: {e}")
        return []

def get_recent_stock_news(cursor, limit=50):
    """Get recent stock news across all tickers"""
    try:
        query = """
        SELECT ticker, company_name, exchange, yahoo_ticker, title, summary, 
               date, image_url, url, provider, created_at
        FROM api_app_stocknews 
        ORDER BY created_at DESC 
        LIMIT %s;
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        stock_news = []
        for row in results:
            stock_news.append({
                'ticker': row[0],
                'company_name': row[1],
                'exchange': row[2],
                'yahoo_ticker': row[3],
                'title': row[4],
                'summary': row[5],
                'date': row[6],
                'image_url': row[7],
                'url': row[8],
                'provider': row[9],
                'created_at': row[10]
            })
        
        return stock_news
        
    except Exception as e:
        logging.error(f"Error getting recent stock news: {e}")
        return []

def delete_old_stock_news(cursor, connection, days_old=90):
    """Delete stock news older than specified days"""
    try:
        delete_query = """
        DELETE FROM api_app_stocknews 
        WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days';
        """
        
        cursor.execute(delete_query, (days_old,))
        deleted_count = cursor.rowcount
        connection.commit()
        
        logging.info(f"Deleted {deleted_count} stock news items older than {days_old} days")
        return deleted_count
        
    except Exception as e:
        logging.error(f"Error deleting old stock news: {e}")
        connection.rollback()
        return 0

def get_stock_news_stats(cursor):
    """Get statistics about stock news in the database"""
    try:
        stats_query = """
        SELECT 
            COUNT(*) as total_news_items,
            COUNT(DISTINCT ticker) as unique_tickers,
            COUNT(DISTINCT provider) as unique_providers,
            MIN(created_at) as oldest_news,
            MAX(created_at) as newest_news
        FROM api_app_stocknews;
        """
        
        cursor.execute(stats_query)
        result = cursor.fetchone()
        
        return {
            'total_news_items': result[0],
            'unique_tickers': result[1],
            'unique_providers': result[2],
            'oldest_news': result[3],
            'newest_news': result[4]
        }
        
    except Exception as e:
        logging.error(f"Error getting stock news stats: {e}")
        return None


# ============================================================================
# SUBSTACK OPERATIONS
# ============================================================================

def insert_substack_post(cursor, connection, title, url, content, subtitle="", image_url="", date=None):
    """Insert a substack post into the database"""
    try:
        # Generate a unique ID
        post_id = str(uuid.uuid4())
        
        # Use current date if no date provided
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        insert_query = """
            INSERT INTO api_app_coppersubstack (id, title, url, content, subtitle, image_url, date, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (url) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                subtitle = EXCLUDED.subtitle,
                image_url = EXCLUDED.image_url,
                date = EXCLUDED.date;
        """
        
        cursor.execute(insert_query, (post_id, title, url, content, subtitle, image_url, date))
        connection.commit()
        logging.info(f"Successfully inserted substack post: {title[:50]}...")
        return True
        
    except Exception as e:
        logging.error(f"Error inserting substack post: {e}")
        connection.rollback()
        return False


def check_substack_url_exists(cursor, url):
    """Check if a substack URL already exists in the database"""
    try:
        check_query = "SELECT COUNT(*) FROM api_app_coppersubstack WHERE url = %s;"
        cursor.execute(check_query, (url,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logging.error(f"Error checking substack URL existence: {e}")
        return False

def get_recent_substack_posts(cursor, limit=20):
    """Get recent substack posts"""
    try:
        query = """
        SELECT id, title, url, content, subtitle, image_url, date, created_at
        FROM api_app_coppersubstack 
        ORDER BY created_at DESC 
        LIMIT %s;
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        posts = []
        for row in results:
            posts.append({
                'id': row[0],
                'title': row[1],
                'url': row[2],
                'content': row[3],
                'subtitle': row[4],
                'image_url': row[5],
                'date': row[6],
                'created_at': row[7]
            })
        
        return posts
        
    except Exception as e:
        logging.error(f"Error getting recent substack posts: {e}")
        return []


# ============================================================================
# YOUTUBE VIDEO OPERATIONS
# ============================================================================

def insert_youtube_video(cursor, connection, video_category, video_link, channel_name, 
                        date, title, company_name=None, stock_ticker=None, 
                        thumbnail_url=None, duration=None, views=None, video_id=None):
    """Insert a YouTube video into the database"""
    try:
        # Generate a unique ID
        video_uuid = str(uuid.uuid4())
        
        # Use current date if no date provided
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        insert_query = """
            INSERT INTO api_app_videopagedata (
                id, video_category, video_link, channel_name, date, title, 
                company_name, stock_ticker, thumbnail_url, duration, views, video_id, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (video_link) DO UPDATE SET
                title = EXCLUDED.title,
                channel_name = EXCLUDED.channel_name,
                date = EXCLUDED.date,
                company_name = EXCLUDED.company_name,
                stock_ticker = EXCLUDED.stock_ticker,
                thumbnail_url = EXCLUDED.thumbnail_url,
                duration = EXCLUDED.duration,
                views = EXCLUDED.views,
                video_id = EXCLUDED.video_id,
                updated_at = CURRENT_TIMESTAMP;
        """
        
        cursor.execute(insert_query, (
            video_uuid, video_category, video_link, channel_name, date, title,
            company_name, stock_ticker, thumbnail_url, duration, views, video_id
        ))
        connection.commit()
        logging.info(f"Successfully inserted YouTube video: {title[:50]}...")
        return True
        
    except Exception as e:
        logging.error(f"Error inserting YouTube video: {e}")
        connection.rollback()
        return False

def check_youtube_video_url_exists(cursor, video_link):
    """Check if a YouTube video URL already exists in the database"""
    try:
        check_query = "SELECT COUNT(*) FROM api_app_videopagedata WHERE video_link = %s;"
        cursor.execute(check_query, (video_link,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logging.error(f"Error checking YouTube video URL existence: {e}")
        return False

def delete_all_youtube_videos(cursor, connection):
    """Delete all YouTube videos from the database"""
    try:
        delete_query = "DELETE FROM api_app_videopagedata;"
        cursor.execute(delete_query)
        deleted_count = cursor.rowcount
        connection.commit()
        logging.info(f"Successfully deleted {deleted_count} YouTube videos from database")
        return deleted_count
    except Exception as e:
        logging.error(f"Error deleting YouTube videos: {e}")
        connection.rollback()
        return 0




def get_youtube_videos_by_category(cursor, category, limit=10):
    """Get YouTube videos by category"""
    try:
        query = """
        SELECT id, video_category, video_link, channel_name, date, title, 
               company_name, stock_ticker, thumbnail_url, duration, views, video_id, created_at
        FROM api_app_videopagedata 
        WHERE video_category = %s 
        ORDER BY created_at DESC 
        LIMIT %s;
        """
        
        cursor.execute(query, (category, limit))
        results = cursor.fetchall()
        
        videos = []
        for row in results:
            videos.append({
                'id': row[0],
                'video_category': row[1],
                'video_link': row[2],
                'channel_name': row[3],
                'date': row[4],
                'title': row[5],
                'company_name': row[6],
                'stock_ticker': row[7],
                'thumbnail_url': row[8],
                'duration': row[9],
                'views': row[10],
                'video_id': row[11],
                'created_at': row[12]
            })
        
        return videos
        
    except Exception as e:
        logging.error(f"Error getting YouTube videos for category {category}: {e}")
        return []

def get_recent_youtube_videos(cursor, limit=20):
    """Get recent YouTube videos across all categories"""
    try:
        query = """
        SELECT id, video_category, video_link, channel_name, date, title, 
               company_name, stock_ticker, thumbnail_url, duration, views, video_id, created_at
        FROM api_app_videopagedata 
        ORDER BY created_at DESC 
        LIMIT %s;
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        videos = []
        for row in results:
            videos.append({
                'id': row[0],
                'video_category': row[1],
                'video_link': row[2],
                'channel_name': row[3],
                'date': row[4],
                'title': row[5],
                'company_name': row[6],
                'stock_ticker': row[7],
                'thumbnail_url': row[8],
                'duration': row[9],
                'views': row[10],
                'video_id': row[11],
                'created_at': row[12]
            })
        
        return videos
        
    except Exception as e:
        logging.error(f"Error getting recent YouTube videos: {e}")
        return []

def get_youtube_video_stats(cursor):
    """Get statistics about YouTube videos in the database"""
    try:
        stats_query = """
        SELECT 
            COUNT(*) as total_videos,
            COUNT(DISTINCT video_category) as unique_categories,
            COUNT(DISTINCT channel_name) as unique_channels,
            COUNT(DISTINCT stock_ticker) as videos_with_tickers,
            MIN(created_at) as oldest_video,
            MAX(created_at) as newest_video
        FROM api_app_videopagedata;
        """
        
        cursor.execute(stats_query)
        result = cursor.fetchone()
        
        return {      
            'total_videos': result[0],
            'unique_categories': result[1],
            'unique_channels': result[2],
            'videos_with_tickers': result[3],
            'oldest_video': result[4],
            'newest_video': result[5]
        }
        
    except Exception as e:
        logging.error(f"Error getting YouTube video stats: {e}")
        return None




def delete_old_youtube_videos(cursor, connection, days_old=30):
    """Delete YouTube videos older than specified days"""
    try:
        delete_query = """
        DELETE FROM api_app_videopagedata 
        WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days';
        """
        
        cursor.execute(delete_query, (days_old,))
        deleted_count = cursor.rowcount
        connection.commit()
        
        logging.info(f"Deleted {deleted_count} YouTube videos older than {days_old} days")
        return deleted_count
        
    except Exception as e:
        logging.error(f"Error deleting old YouTube videos: {e}")
        connection.rollback()
        return 0



# ============================================================================
# GENERAL NEWS OPERATIONS
# ============================================================================

def insert_general_news(cursor, connection, source, title, url, content=None, summary=None, image_url=None, date=None):
    """Insert a general news article into the database"""
    try:
        # Generate a unique ID
        news_id = str(uuid.uuid4())
        
        # Use current date if no date provided
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        insert_query = """
            INSERT INTO api_app_generalnews (
                id, source, title, url, content, summary, image_url, date, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (url) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                summary = EXCLUDED.summary,
                image_url = EXCLUDED.image_url,
                date = EXCLUDED.date,
                updated_at = CURRENT_TIMESTAMP;
        """
        
        cursor.execute(insert_query, (news_id, source, title, url, content, summary, image_url, date))
        connection.commit()
        logging.info(f"Successfully inserted general news: {title[:50]}...")
        return True
        
    except Exception as e:
        logging.error(f"Error inserting general news: {e}")
        connection.rollback()
        return False

def check_general_news_url_exists(cursor, url):
    """Check if a general news URL already exists in the database"""
    try:
        check_query = "SELECT COUNT(*) FROM api_app_generalnews WHERE url = %s;"
        cursor.execute(check_query, (url,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logging.error(f"Error checking general news URL existence: {e}")
        return False

def get_recent_general_news(cursor, limit=50, source=None):
    """Get recent general news articles"""
    try:
        if source:
            query = """
            SELECT id, source, title, url, content, summary, image_url, date, created_at
            FROM api_app_generalnews 
            WHERE source = %s
            ORDER BY created_at DESC 
            LIMIT %s;
            """
            cursor.execute(query, (source, limit))
        else:
            query = """
            SELECT id, source, title, url, content, summary, image_url, date, created_at
            FROM api_app_generalnews 
            ORDER BY created_at DESC 
            LIMIT %s;
            """
            cursor.execute(query, (limit,))
        
        results = cursor.fetchall()
        
        news = []
        for row in results:
            news.append({
                'id': row[0],
                'source': row[1],
                'title': row[2],
                'url': row[3],
                'content': row[4],
                'summary': row[5],
                'image_url': row[6],
                'date': row[7],
                'created_at': row[8]
            })
        
        return news
        
    except Exception as e:
        logging.error(f"Error getting recent general news: {e}")
        return []

def get_general_news_stats(cursor):
    """Get statistics about general news in the database"""
    try:
        stats_query = """
        SELECT 
            COUNT(*) as total_articles,
            COUNT(DISTINCT source) as unique_sources,
            MIN(created_at) as oldest_article,
            MAX(created_at) as newest_article,
            COUNT(CASE WHEN image_url IS NOT NULL THEN 1 END) as articles_with_images
        FROM api_app_generalnews;
        """
        
        cursor.execute(stats_query)
        result = cursor.fetchone()
        
        return {
            'total_articles': result[0],
            'unique_sources': result[1],
            'oldest_article': result[2],
            'newest_article': result[3],
            'articles_with_images': result[4]
        }
        
    except Exception as e:
        logging.error(f"Error getting general news stats: {e}")
        return None

def delete_old_general_news(cursor, connection, days_old=90):
    """Delete general news articles older than specified days"""
    try:
        delete_query = """
        DELETE FROM api_app_generalnews 
        WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days';
        """
        
        cursor.execute(delete_query, (days_old,))
        deleted_count = cursor.rowcount
        connection.commit()
        
        logging.info(f"Deleted {deleted_count} general news articles older than {days_old} days")
        return deleted_count
        
    except Exception as e:
        logging.error(f"Error deleting old general news: {e}")
        connection.rollback()
        return 0


# ============================================================================
# GENERAL NEWS OPERATIONS
# ============================================================================

def insert_general_news(cursor, connection, source, title, url, content=None, summary=None, image_url=None, date=None):
    """Insert a general news article into the database"""
    try:
        # Generate a unique ID
        news_id = str(uuid.uuid4())
        
        # Use current date if no date provided
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        insert_query = """
            INSERT INTO api_app_generalnews (
                id, source, title, url, content, summary, image_url, date, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (url) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                summary = EXCLUDED.summary,
                image_url = EXCLUDED.image_url,
                date = EXCLUDED.date,
                updated_at = CURRENT_TIMESTAMP;
        """
        
        cursor.execute(insert_query, (news_id, source, title, url, content, summary, image_url, date))
        connection.commit()
        logging.info(f"Successfully inserted general news: {title[:50]}...")
        return True
        
    except Exception as e:
        logging.error(f"Error inserting general news: {e}")
        connection.rollback()
        return False

def check_general_news_url_exists(cursor, url):
    """Check if a general news URL already exists in the database"""
    try:
        check_query = "SELECT COUNT(*) FROM api_app_generalnews WHERE url = %s;"
        cursor.execute(check_query, (url,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logging.error(f"Error checking general news URL existence: {e}")
        return False

def get_recent_general_news(cursor, limit=50, source=None):
    """Get recent general news articles"""
    try:
        if source:
            query = """
            SELECT id, source, title, url, content, summary, image_url, date, created_at
            FROM api_app_generalnews 
            WHERE source = %s
            ORDER BY created_at DESC 
            LIMIT %s;
            """
            cursor.execute(query, (source, limit))
        else:
            query = """
            SELECT id, source, title, url, content, summary, image_url, date, created_at
            FROM api_app_generalnews 
            ORDER BY created_at DESC 
            LIMIT %s;
            """
            cursor.execute(query, (limit,))
        
        results = cursor.fetchall()
        
        news = []
        for row in results:
            news.append({
                'id': row[0],
                'source': row[1],
                'title': row[2],
                'url': row[3],
                'content': row[4],
                'summary': row[5],
                'image_url': row[6],
                'date': row[7],
                'created_at': row[8]
            })
        
        return news
        
    except Exception as e:
        logging.error(f"Error getting recent general news: {e}")
        return []

def get_general_news_stats(cursor):
    """Get statistics about general news in the database"""
    try:
        stats_query = """
        SELECT 
            COUNT(*) as total_articles,
            COUNT(DISTINCT source) as unique_sources,
            MIN(created_at) as oldest_article,
            MAX(created_at) as newest_article,
            COUNT(CASE WHEN image_url IS NOT NULL THEN 1 END) as articles_with_images
        FROM api_app_generalnews;
        """
        
        cursor.execute(stats_query)
        result = cursor.fetchone()
        
        return {
            'total_articles': result[0],
            'unique_sources': result[1],
            'oldest_article': result[2],
            'newest_article': result[3],
            'articles_with_images': result[4]
        }
        
    except Exception as e:
        logging.error(f"Error getting general news stats: {e}")
        return None

def delete_old_general_news(cursor, connection, days_old=90):
    """Delete general news articles older than specified days"""
    try:
        delete_query = """
        DELETE FROM api_app_generalnews 
        WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days';
        """
        
        cursor.execute(delete_query, (days_old,))
        deleted_count = cursor.rowcount
        connection.commit()
        
        logging.info(f"Deleted {deleted_count} general news articles older than {days_old} days")
        return deleted_count
        
    except Exception as e:
        logging.error(f"Error deleting old general news: {e}")
        connection.rollback()
        return 0


# ============================================================================
# GENERAL NEWS OPERATIONS
# ============================================================================

def insert_general_news(cursor, connection, source, title, url, content=None, summary=None, image_url=None, date=None):
    """Insert a general news article into the database"""
    try:
        # Generate a unique ID
        news_id = str(uuid.uuid4())
        
        # Use current date if no date provided
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        insert_query = """
            INSERT INTO api_app_generalnews (
                id, source, title, url, content, summary, image_url, date, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (url) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                summary = EXCLUDED.summary,
                image_url = EXCLUDED.image_url,
                date = EXCLUDED.date,
                updated_at = CURRENT_TIMESTAMP;
        """
        
        cursor.execute(insert_query, (news_id, source, title, url, content, summary, image_url, date))
        connection.commit()
        logging.info(f"Successfully inserted general news: {title[:50]}...")
        return True
        
    except Exception as e:
        logging.error(f"Error inserting general news: {e}")
        connection.rollback()
        return False

def check_general_news_url_exists(cursor, url):
    """Check if a general news URL already exists in the database"""
    try:
        check_query = "SELECT COUNT(*) FROM api_app_generalnews WHERE url = %s;"
        cursor.execute(check_query, (url,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logging.error(f"Error checking general news URL existence: {e}")
        return False

def get_recent_general_news(cursor, limit=50, source=None):
    """Get recent general news articles"""
    try:
        if source:
            query = """
            SELECT id, source, title, url, content, summary, image_url, date, created_at
            FROM api_app_generalnews 
            WHERE source = %s
            ORDER BY created_at DESC 
            LIMIT %s;
            """
            cursor.execute(query, (source, limit))
        else:
            query = """
            SELECT id, source, title, url, content, summary, image_url, date, created_at
            FROM api_app_generalnews 
            ORDER BY created_at DESC 
            LIMIT %s;
            """
            cursor.execute(query, (limit,))
        
        results = cursor.fetchall()
        
        news = []
        for row in results:
            news.append({
                'id': row[0],
                'source': row[1],
                'title': row[2],
                'url': row[3],
                'content': row[4],
                'summary': row[5],
                'image_url': row[6],
                'date': row[7],
                'created_at': row[8]
            })
        
        return news
        
    except Exception as e:
        logging.error(f"Error getting recent general news: {e}")
        return []

def get_general_news_stats(cursor):
    """Get statistics about general news in the database"""
    try:
        stats_query = """
        SELECT 
            COUNT(*) as total_articles,
            COUNT(DISTINCT source) as unique_sources,
            MIN(created_at) as oldest_article,
            MAX(created_at) as newest_article,
            COUNT(CASE WHEN image_url IS NOT NULL THEN 1 END) as articles_with_images
        FROM api_app_generalnews;
        """
        
        cursor.execute(stats_query)
        result = cursor.fetchone()
        
        return {
            'total_articles': result[0],
            'unique_sources': result[1],
            'oldest_article': result[2],
            'newest_article': result[3],
            'articles_with_images': result[4]
        }
        
    except Exception as e:
        logging.error(f"Error getting general news stats: {e}")
        return None

def delete_old_general_news(cursor, connection, days_old=90):
    """Delete general news articles older than specified days"""
    try:
        delete_query = """
        DELETE FROM api_app_generalnews 
        WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days';
        """
        
        cursor.execute(delete_query, (days_old,))
        deleted_count = cursor.rowcount
        connection.commit()
        
        logging.info(f"Deleted {deleted_count} general news articles older than {days_old} days")
        return deleted_count
        
    except Exception as e:
        logging.error(f"Error deleting old general news: {e}")
        connection.rollback()
        return 0
