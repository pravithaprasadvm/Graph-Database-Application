#!/usr/bin/env python3
"""
Seed Script for CognoDB Cloud Database
Populates CognoDB Cloud instance with a realistic Multi-Tier Supply Chain Disruption & Risk Graph.
"""

import sys
import logging
from backend.config import config
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed")

CYPHER_CLEAR_DB = "MATCH (n) DETACH DELETE n"

# Parameterized Node Creation Queries
NODES_DATA = [
    # Products
    ("Product", {"id": "PROD-101", "name": "QuantumDrive Server X", "category": "Enterprise Hardware", "quarterly_revenue_m": 42.5}),
    ("Product", {"id": "PROD-102", "name": "Solaris EV Battery Pack", "category": "Automotive CleanTech", "quarterly_revenue_m": 88.0}),
    ("Product", {"id": "PROD-103", "name": "AeroX Jet Turbine ECU", "category": "Aerospace Avionics", "quarterly_revenue_m": 65.2}),
    ("Product", {"id": "PROD-104", "name": "Nexus 6G Edge Router", "category": "Telecommunications", "quarterly_revenue_m": 31.0}),

    # Assemblies
    ("Assembly", {"id": "ASSY-201", "name": "Power Distribution Unit", "complexity": "High"}),
    ("Assembly", {"id": "ASSY-202", "name": "Li-Ion Thermal Cell Array", "complexity": "Critical"}),
    ("Assembly", {"id": "ASSY-203", "name": "High-Frequency Optical Controller", "complexity": "High"}),
    ("Assembly", {"id": "ASSY-204", "name": "Signal Processing Subsystem", "complexity": "Medium"}),

    # Components
    ("Component", {"id": "COMP-301", "name": "3nm SiC Power MOSFET", "category": "Semiconductors", "is_sole_source": True}),
    ("Component", {"id": "COMP-302", "name": "Neodymium Permanent Magnet", "category": "Raw Materials", "is_sole_source": False}),
    ("Component", {"id": "COMP-303", "name": "Gallium Nitride Transceiver IC", "category": "Semiconductors", "is_sole_source": True}),
    ("Component", {"id": "COMP-304", "name": "Prismatic Li-Ion Cell", "category": "Battery Tech", "is_sole_source": False}),
    ("Component", {"id": "COMP-305", "name": "FPGA Cryptographic Unit", "category": "Chips", "is_sole_source": True}),

    # Suppliers
    ("Supplier", {"id": "SUPP-401", "name": "Taiwan Semi Foundry (TSMC)", "tier": 1, "rating": 4.9}),
    ("Supplier", {"id": "SUPP-402", "name": "Sumitomo Rare Earths", "tier": 2, "rating": 4.5}),
    ("Supplier", {"id": "SUPP-403", "name": "Bosch Auto Systems", "tier": 1, "rating": 4.8}),
    ("Supplier", {"id": "SUPP-404", "name": "Infineon Technologies", "tier": 1, "rating": 4.7}),
    ("Supplier", {"id": "SUPP-405", "name": "GlobalFoundries Dresden", "tier": 2, "rating": 4.4}),
    ("Supplier", {"id": "SUPP-406", "name": "Samsung Electronics Semiconductor", "tier": 2, "rating": 4.8}),

    # Facilities
    ("Facility", {"id": "FAC-501", "name": "Hsinchu Fab 12", "type": "Fab Semiconductor"}),
    ("Facility", {"id": "FAC-502", "name": "Kyoto Metal Refinery", "type": "Processing Plant"}),
    ("Facility", {"id": "FAC-503", "name": "Stuttgart Industrial Hub", "type": "Assembly Plant"}),
    ("Facility", {"id": "FAC-504", "name": "Dresden Wafer Fab", "type": "Fab Semiconductor"}),

    # Regions
    ("Region", {"id": "REG-601", "name": "East Asia (Taiwan Channel)", "risk_index": "High"}),
    ("Region", {"id": "REG-602", "name": "Western Europe (Germany)", "risk_index": "Low"}),
    ("Region", {"id": "REG-603", "name": "Japan Inland Logistics", "risk_index": "Medium"}),

    # Disruption Events
    ("DisruptionEvent", {"id": "DISR-701", "name": "Typhoon Gaemi Port Lockout", "severity": "CRITICAL", "type": "Weather Disaster"}),
    ("DisruptionEvent", {"id": "DISR-702", "name": "European Grid Outage & Energy Cap", "severity": "HIGH", "type": "Infrastructure Crisis"}),
    ("DisruptionEvent", {"id": "DISR-703", "name": "Lithium Export Tariff Restrictions", "severity": "MEDIUM", "type": "Geopolitical Policy"})
]

RELATIONSHIPS_DATA = [
    # Product -> Assembly
    ("PROD-101", "ASSY-201", "REQUIRES_ASSEMBLY", {"quantity": 2}),
    ("PROD-101", "ASSY-204", "REQUIRES_ASSEMBLY", {"quantity": 1}),
    ("PROD-102", "ASSY-202", "REQUIRES_ASSEMBLY", {"quantity": 12}),
    ("PROD-103", "ASSY-203", "REQUIRES_ASSEMBLY", {"quantity": 4}),
    ("PROD-104", "ASSY-204", "REQUIRES_ASSEMBLY", {"quantity": 2}),
    ("PROD-104", "ASSY-201", "REQUIRES_ASSEMBLY", {"quantity": 1}),

    # Assembly -> Component
    ("ASSY-201", "COMP-301", "USES_COMPONENT", {"quantity": 8}),
    ("ASSY-201", "COMP-305", "USES_COMPONENT", {"quantity": 2}),
    ("ASSY-202", "COMP-304", "USES_COMPONENT", {"quantity": 96}),
    ("ASSY-202", "COMP-302", "USES_COMPONENT", {"quantity": 24}),
    ("ASSY-203", "COMP-303", "USES_COMPONENT", {"quantity": 4}),
    ("ASSY-204", "COMP-305", "USES_COMPONENT", {"quantity": 1}),

    # Component -> Supplier
    ("COMP-301", "SUPP-401", "SUPPLIED_BY", {"lead_time_days": 45, "cost_usd": 120.0}),
    ("COMP-302", "SUPP-402", "SUPPLIED_BY", {"lead_time_days": 20, "cost_usd": 15.0}),
    ("COMP-303", "SUPP-404", "SUPPLIED_BY", {"lead_time_days": 30, "cost_usd": 85.0}),
    ("COMP-304", "SUPP-403", "SUPPLIED_BY", {"lead_time_days": 15, "cost_usd": 40.0}),
    ("COMP-305", "SUPP-401", "SUPPLIED_BY", {"lead_time_days": 60, "cost_usd": 210.0}),

    # Supplier -> Facility
    ("SUPP-401", "FAC-501", "OPERATES_FACILITY", {}),
    ("SUPP-402", "FAC-502", "OPERATES_FACILITY", {}),
    ("SUPP-403", "FAC-503", "OPERATES_FACILITY", {}),
    ("SUPP-404", "FAC-504", "OPERATES_FACILITY", {}),

    # Facility -> Region
    ("FAC-501", "REG-601", "LOCATED_IN", {}),
    ("FAC-502", "REG-603", "LOCATED_IN", {}),
    ("FAC-503", "REG-602", "LOCATED_IN", {}),
    ("FAC-504", "REG-602", "LOCATED_IN", {}),

    # Disruption -> Region/Facility
    ("DISR-701", "REG-601", "AFFECTS_REGION", {"severity": "CRITICAL"}),
    ("DISR-702", "REG-602", "AFFECTS_REGION", {"severity": "HIGH"}),
    ("DISR-703", "FAC-502", "DIRECTLY_IMPACTS", {"impact_score": 0.85}),

    # Alternative Suppliers
    ("SUPP-405", "SUPP-401", "ALTERNATIVE_FOR", {"switching_days": 14, "added_cost_percent": 12.5}),
    ("SUPP-406", "SUPP-401", "ALTERNATIVE_FOR", {"switching_days": 21, "added_cost_percent": 8.0})
]

def run_seed():
    logger.info("Initializing CognoDB Cloud Seed Script...")
    if not config.is_configured():
        logger.warning("COGNO_URI/COGNO_PASSWORD not configured in .env. Seed script requires active CognoDB credentials.")
        return False

    try:
        driver = GraphDatabase.driver(config.COGNO_URI, auth=(config.COGNO_USER, config.COGNO_PASSWORD))
        driver.verify_connectivity()
        logger.info("Connected to CognoDB Cloud successfully.")

        with driver.session() as session:
            logger.info("Clearing old data from CognoDB graph...")
            session.run(CYPHER_CLEAR_DB)

            logger.info("Creating Nodes...")
            for label, props in NODES_DATA:
                cypher = f"CREATE (n:{label} $props)"
                session.run(cypher, props=props)
            logger.info(f"Created {len(NODES_DATA)} nodes.")

            logger.info("Creating Relationships...")
            for src_id, target_id, rel_type, rel_props in RELATIONSHIPS_DATA:
                cypher = f"""
                MATCH (a {repr("{id: $src_id}")}), (b {repr("{id: $target_id}")})
                CREATE (a)-[r:{rel_type} $rel_props]->(b)
                """
                session.run(cypher, src_id=src_id, target_id=target_id, rel_props=rel_props)
            logger.info(f"Created {len(RELATIONSHIPS_DATA)} relationships.")

            # Summary verification
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            count = result.single()["node_count"]
            logger.info(f"Seed complete! CognoDB now contains {count} nodes.")
            
        driver.close()
        return True
    except Exception as e:
        logger.error(f"Seeding failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_seed()
    sys.exit(0 if success else 1)
