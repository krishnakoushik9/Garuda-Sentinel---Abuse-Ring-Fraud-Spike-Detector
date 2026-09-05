import os
from src.pipeline.neo4j_loader import Neo4jLoader

def seed_and_analyze():
    print("=== Phase 1: Seeding Neo4j from SQLite ===")
    loader = Neo4jLoader()
    if not loader.enabled:
        print("Neo4j not reachable. Aborting seed.")
        return

    try:
        # Load real data using the updated batched methods
        loader.load_accounts(batch_size=500)
        loader.load_transactions(batch_size=500)
        
        print("\n=== Phase 2: Running GDS Analytics (Louvain) ===")
        with loader.driver.session() as session:
            # Drop existing projection if any
            print("Cleaning up old GDS projections...")
            session.run("CALL gds.graph.drop('fraud_graph', false)")
            
            # Project graph
            print("Projecting graph 'fraud_graph' in GDS...")
            session.run("""
            CALL gds.graph.project(
                'fraud_graph',
                'Account',
                'SENT_TO',
                { relationshipProperties: 'amount' }
            )
            """)
            
            # Run Louvain
            print("Computing Louvain communities and writing back 'community_id'...")
            session.run("""
            CALL gds.louvain.write('fraud_graph', { writeProperty: 'community_id' })
            """)
            
            # Run PageRank for further enrichment
            print("Computing PageRank scores and writing back 'pagerank'...")
            session.run("""
            CALL gds.pageRank.write('fraud_graph', { writeProperty: 'pagerank' })
            """)
            
            print("GDS Analytics complete. 'community_id' and 'pagerank' stored successfully.")
    except Exception as e:
        print(f"GDS Analytics failed: {e}. Ensure Neo4j GDS plugin is active.")
    finally:
        loader.close()

if __name__ == "__main__":
    seed_and_analyze()
