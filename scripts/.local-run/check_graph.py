import psycopg2
c=psycopg2.connect(host="127.0.0.1",port=5432,dbname="postgres",user="postgres",password="root")
c.autocommit=True
cur=c.cursor()
cur.execute("SELECT nspname FROM pg_namespace WHERE nspname='graph'")
print("schema", cur.fetchone())
cur.execute("SELECT version, checksum, description FROM graph.flyway_schema_history ORDER BY installed_rank")
print("history", cur.fetchall())
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='graph' AND table_name='t_graph' ORDER BY ordinal_position")
print("cols", [r[0] for r in cur.fetchall()])
