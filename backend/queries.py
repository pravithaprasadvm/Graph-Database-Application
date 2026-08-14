"""
Parameterized Cypher Queries for CognoDB Graph Analytics
"""

# Query 1: Graph Overview (Nodes & Relationships)
CYPHER_GRAPH_OVERVIEW = """
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m LIMIT $limit
"""

# Query 2: Multi-hop Disruption Blast-Radius Analysis (2 to 5 hops)
# Traverses: DisruptionEvent -> Region/Facility -> Supplier -> Component -> Assembly -> Product
CYPHER_DISRUPTION_BLAST_RADIUS = """
MATCH (d:DisruptionEvent)
WHERE d.id = $disruption_id OR d.name = $disruption_id
MATCH (d)-[:AFFECTS_REGION|DIRECTLY_IMPACTS*1..2]->(target)
MATCH path = (target)-[:OPERATES_FACILITY|SUPPLIED_BY|USES_COMPONENT|REQUIRES_ASSEMBLY*1..4]->(p:Product)
RETURN d, target, path, p,
       length(path) as hops,
       nodes(path) as path_nodes,
       relationships(path) as path_rels
"""

# Query 3: Single Point of Failure (SPOF) & Bottleneck Discovery
# Relational-awkward query matching components with sole suppliers and calculating multi-hop product exposure
CYPHER_SINGLE_POINTS_OF_FAILURE = """
MATCH (c:Component)-[:SUPPLIED_BY]->(s:Supplier)
WITH c, collect(s) as suppliers
WHERE size(suppliers) = 1
MATCH (p:Product)-[:REQUIRES_ASSEMBLY|USES_COMPONENT*1..2]->(c)
RETURN c.id as component_id,
       c.name as component_name,
       c.category as category,
       suppliers[0].name as sole_supplier,
       suppliers[0].id as sole_supplier_id,
       collect(DISTINCT p.name) as affected_products,
       count(DISTINCT p) as product_count,
       sum(p.quarterly_revenue_m) as revenue_at_risk_m
ORDER BY revenue_at_risk_m DESC
"""

# Query 4: Multi-hop Alternate Supply Path Discovery
# Find 2-hop alternate supplier routes with lead time and cost metrics
CYPHER_FIND_ALTERNATE_SUPPLIERS = """
MATCH (c:Component)-[:SUPPLIED_BY]->(primary:Supplier)
WHERE primary.id = $supplier_id OR primary.name = $supplier_id
MATCH (alt:Supplier)-[rel:ALTERNATIVE_FOR]->(primary)
RETURN c.name as component,
       primary.name as primary_supplier,
       alt.id as alt_supplier_id,
       alt.name as alt_supplier,
       alt.rating as alt_rating,
       alt.lead_time_days as lead_time_days,
       rel.switching_days as switching_days,
       rel.added_cost_percent as extra_cost_pct
ORDER BY rel.switching_days ASC, alt.rating DESC
"""

# Query 5: N-Tier Deep Product Lineage (Multi-hop tree)
CYPHER_PRODUCT_LINEAGE = """
MATCH path = (p:Product)-[:REQUIRES_ASSEMBLY|USES_COMPONENT|SUPPLIED_BY|OPERATES_FACILITY|LOCATED_IN*1..5]->(node)
WHERE p.id = $product_id OR p.name = $product_id
RETURN path
"""

# Query 6: Graph Summary Statistics
CYPHER_GRAPH_STATS = """
MATCH (n)
WITH labels(n) as node_labels, count(n) as label_count
UNWIND node_labels as label
RETURN label, sum(label_count) as count
"""
