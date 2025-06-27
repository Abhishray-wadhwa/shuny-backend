import psycopg2

conn = psycopg2.connect(
    host="aws-0-ap-southeast-1.pooler.supabase.com",
    port="6543",
    database="postgres",
    user="postgres.yjfczkcpcdagxpdrbynf",
    password="supercalifragilastic"
)

print("✅ Connected!")
