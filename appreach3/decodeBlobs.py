import msgpack
import psycopg
from psycopg.rows import dict_row
import json

def decode_all_blobs(conn_string: str):
    """Simply decode and print all blobs from checkpoint_blobs table"""
    
    with psycopg.connect(
        conn_string, 
        autocommit=True, 
        prepare_threshold=0, 
        row_factory=dict_row
    ) as conn:
        cursor = conn.cursor()
        
        # Get all blobs
        query = """
        SELECT thread_id, channel, version, blob 
        FROM checkpoint_blobs 
        ORDER BY thread_id, channel, version
        """
        cursor.execute(query)
        
        for row in cursor.fetchall():
            try:
                # Decode the msgpack blob
                decoded_data = msgpack.unpackb(row['blob'], raw=False, strict_map_key=False)
                
                print(f"Thread: {row['thread_id']} | Channel: {row['channel']} | Version: {row['version']}")
                print(json.dumps(decoded_data, indent=2, default=str))
                print("-" * 80)
                
            except Exception as e:
                print(f"Error decoding blob: {e}")
    # Usage
if __name__ == "__main__":
    # Replace with your connection string
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    conn_string = os.getenv("POSTGRESQL_CONNECTION_STRING")

    decode_all_blobs(conn_string)