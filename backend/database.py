import logging
import traceback
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, Driver, Session, exceptions
from backend.config import config

logger = logging.getLogger("cognodb")
logger.setLevel(logging.INFO)

# In-memory mock dataset for fallback/testing when database is offline or unconfigured
MOCK_NODES = [
    # Products
    {"id": "PROD-101", "label": "Product", "name": "QuantumDrive Server X", "category": "Enterprise Hardware", "quarterly_revenue_m": 42.5},
    {"id": "PROD-102", "label": "Product", "name": "Solaris EV Battery Pack", "category": "Automotive CleanTech", "quarterly_revenue_m": 88.0},
    {"id": "PROD-103", "label": "Product", "name": "AeroX Jet Turbine ECU", "category": "Aerospace Avionics", "quarterly_revenue_m": 65.2},
    {"id": "PROD-104", "label": "Product", "name": "Nexus 6G Edge Router", "category": "Telecommunications", "quarterly_revenue_m": 31.0},
    
    # Assemblies
    {"id": "ASSY-201", "label": "Assembly", "name": "Power Distribution Unit", "complexity": "High"},
    {"id": "ASSY-202", "label": "Assembly", "name": "Li-Ion Thermal Cell Array", "complexity": "Critical"},
    {"id": "ASSY-203", "label": "Assembly", "name": "High-Frequency Optical Controller", "complexity": "High"},
    {"id": "ASSY-204", "label": "Assembly", "name": "Signal Processing Subsystem", "complexity": "Medium"},

    # Components
    {"id": "COMP-301", "label": "Component", "name": "3nm SiC Power MOSFET", "category": "Semiconductors", "is_sole_source": True},
    {"id": "COMP-302", "label": "Component", "name": "Neodymium Permanent Magnet", "category": "Raw Materials", "is_sole_source": False},
    {"id": "COMP-303", "label": "Component", "name": "Gallium Nitride Transceiver IC", "category": "Semiconductors", "is_sole_source": True},
    {"id": "COMP-304", "label": "Component", "name": "Prismatic Li-Ion Cell", "category": "Battery Tech", "is_sole_source": False},
    {"id": "COMP-305", "label": "Component", "name": "FPGA Cryptographic Unit", "category": "Chips", "is_sole_source": True},

    # Suppliers
    {"id": "SUPP-401", "label": "Supplier", "name": "Taiwan Semi Foundry (TSMC)", "tier": 1, "rating": 4.9},
    {"id": "SUPP-402", "label": "Supplier", "name": "Sumitomo Rare Earths", "tier": 2, "rating": 4.5},
    {"id": "SUPP-403", "label": "Supplier", "name": "Bosch Auto Systems", "tier": 1, "rating": 4.8},
    {"id": "SUPP-404", "label": "Supplier", "name": "Infineon Technologies", "tier": 1, "rating": 4.7},
    {"id": "SUPP-405", "label": "Supplier", "name": "GlobalFoundries Dresden", "tier": 2, "rating": 4.4},
    {"id": "SUPP-406", "label": "Supplier", "name": "Samsung Electronics Semiconductor", "tier": 2, "rating": 4.8},

    # Facilities
    {"id": "FAC-501", "label": "Facility", "name": "Hsinchu Fab 12", "type": "Fab Semiconductor"},
    {"id": "FAC-502", "label": "Facility", "name": "Kyoto Metal Refinery", "type": "Processing Plant"},
    {"id": "FAC-503", "label": "Facility", "name": "Stuttgart Industrial Hub", "type": "Assembly Plant"},
    {"id": "FAC-504", "label": "Facility", "name": "Dresden Wafer Fab", "type": "Fab Semiconductor"},

    # Regions
    {"id": "REG-601", "label": "Region", "name": "East Asia (Taiwan Channel)", "risk_index": "High"},
    {"id": "REG-602", "label": "Region", "name": "Western Europe (Germany)", "risk_index": "Low"},
    {"id": "REG-603", "label": "Region", "name": "Japan Inland Logistics", "risk_index": "Medium"},

    # Disruption Events
    {"id": "DISR-701", "label": "DisruptionEvent", "name": "Typhoon Gaemi Port Lockout", "severity": "CRITICAL", "type": "Weather Disaster"},
    {"id": "DISR-702", "label": "DisruptionEvent", "name": "European Grid Outage & Energy Cap", "severity": "HIGH", "type": "Infrastructure Crisis"},
    {"id": "DISR-703", "label": "DisruptionEvent", "name": "Lithium Export Tariff Restrictions", "severity": "MEDIUM", "type": "Geopolitical Policy"}
]

MOCK_RELATIONSHIPS = [
    # Product -> Assembly
    {"source": "PROD-101", "target": "ASSY-201", "type": "REQUIRES_ASSEMBLY", "quantity": 2},
    {"source": "PROD-101", "target": "ASSY-204", "type": "REQUIRES_ASSEMBLY", "quantity": 1},
    {"source": "PROD-102", "target": "ASSY-202", "type": "REQUIRES_ASSEMBLY", "quantity": 12},
    {"source": "PROD-103", "target": "ASSY-203", "type": "REQUIRES_ASSEMBLY", "quantity": 4},
    {"source": "PROD-104", "target": "ASSY-204", "type": "REQUIRES_ASSEMBLY", "quantity": 2},
    {"source": "PROD-104", "target": "ASSY-201", "type": "REQUIRES_ASSEMBLY", "quantity": 1},

    # Assembly -> Component
    {"source": "ASSY-201", "target": "COMP-301", "type": "USES_COMPONENT", "quantity": 8},
    {"source": "ASSY-201", "target": "COMP-305", "type": "USES_COMPONENT", "quantity": 2},
    {"source": "ASSY-202", "target": "COMP-304", "type": "USES_COMPONENT", "quantity": 96},
    {"source": "ASSY-202", "target": "COMP-302", "type": "USES_COMPONENT", "quantity": 24},
    {"source": "ASSY-203", "target": "COMP-303", "type": "USES_COMPONENT", "quantity": 4},
    {"source": "ASSY-204", "target": "COMP-305", "type": "USES_COMPONENT", "quantity": 1},

    # Component -> Supplier
    {"source": "COMP-301", "target": "SUPP-401", "type": "SUPPLIED_BY", "lead_time_days": 45, "cost_usd": 120.0},
    {"source": "COMP-302", "target": "SUPP-402", "type": "SUPPLIED_BY", "lead_time_days": 20, "cost_usd": 15.0},
    {"source": "COMP-303", "target": "SUPP-404", "type": "SUPPLIED_BY", "lead_time_days": 30, "cost_usd": 85.0},
    {"source": "COMP-304", "target": "SUPP-403", "type": "SUPPLIED_BY", "lead_time_days": 15, "cost_usd": 40.0},
    {"source": "COMP-305", "target": "SUPP-401", "type": "SUPPLIED_BY", "lead_time_days": 60, "cost_usd": 210.0},

    # Supplier -> Facility & Location
    {"source": "SUPP-401", "target": "FAC-501", "type": "OPERATES_FACILITY"},
    {"source": "SUPP-402", "target": "FAC-502", "type": "OPERATES_FACILITY"},
    {"source": "SUPP-403", "target": "FAC-503", "type": "OPERATES_FACILITY"},
    {"source": "SUPP-404", "target": "FAC-504", "type": "OPERATES_FACILITY"},
    
    {"source": "FAC-501", "target": "REG-601", "type": "LOCATED_IN"},
    {"source": "FAC-502", "target": "REG-603", "type": "LOCATED_IN"},
    {"source": "FAC-503", "target": "REG-602", "type": "LOCATED_IN"},
    {"source": "FAC-504", "target": "REG-602", "type": "LOCATED_IN"},

    # Disruption -> Region/Facility
    {"source": "DISR-701", "target": "REG-601", "type": "AFFECTS_REGION", "severity": "CRITICAL"},
    {"source": "DISR-702", "target": "REG-602", "type": "AFFECTS_REGION", "severity": "HIGH"},
    {"source": "DISR-703", "target": "FAC-502", "type": "DIRECTLY_IMPACTS", "impact_score": 0.85},

    # Alternative Suppliers
    {"source": "SUPP-405", "target": "SUPP-401", "type": "ALTERNATIVE_FOR", "switching_days": 14, "added_cost_percent": 12.5},
    {"source": "SUPP-406", "target": "SUPP-401", "type": "ALTERNATIVE_FOR", "switching_days": 21, "added_cost_percent": 8.0}
]

class CognoDBManager:
    """Manager for CognoDB Cloud connection over Neo4j Bolt Driver with mock fallback."""
    
    def __init__(self):
        self._driver: Optional[Driver] = None
        self.is_live: bool = False
        self.connection_error: Optional[str] = None
        self._try_connect()

    def _try_connect(self):
        """Attempts connection to CognoDB Cloud using official Neo4j Driver over bolt+s."""
        if not config.is_configured():
            self.is_live = False
            self.connection_error = "CognoDB credentials not configured in environment (.env). Running in high-performance Demo Engine mode."
            logger.warning(self.connection_error)
            return

        try:
            logger.info(f"Connecting to CognoDB Cloud at {config.COGNO_URI} with user '{config.COGNO_USER}'...")
            self._driver = GraphDatabase.driver(
                config.COGNO_URI,
                auth=(config.COGNO_USER, config.COGNO_PASSWORD)
            )
            # Verify connection
            self._driver.verify_connectivity()
            self.is_live = True
            self.connection_error = None
            logger.info("Successfully connected to CognoDB Cloud!")
        except Exception as e:
            self.is_live = False
            self.connection_error = f"Failed to connect to CognoDB Cloud at {config.COGNO_URI}: {str(e)}"
            logger.error(self.connection_error)

    def get_status(self) -> Dict[str, Any]:
        """Returns database status information."""
        return {
            "is_live": self.is_live,
            "uri": config.COGNO_URI if config.is_configured() else "Demo Mode (Mock Engine)",
            "user": config.COGNO_USER,
            "status": "CONNECTED_LIVE" if self.is_live else "FALLBACK_DEMO_MODE",
            "connection_error": self.connection_error,
            "node_count": len(MOCK_NODES) if not self.is_live else self._get_live_count()
        }

    def _get_live_count(self) -> int:
        try:
            res = self.execute_query("MATCH (n) RETURN count(n) as count")
            if res and res.get("records"):
                return res["records"][0].get("count", 0)
        except Exception:
            pass
        return 0

    def execute_query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a Cypher query against live CognoDB or fallback engine."""
        if parameters is None:
            parameters = {}

        if self.is_live and self._driver:
            try:
                with self._driver.session() as session:
                    result = session.run(cypher, parameters)
                    records = []
                    nodes_dict = {}
                    relationships_list = []

                    for rec in result:
                        record_dict = {}
                        for key in rec.keys():
                            val = rec[key]
                            record_dict[key] = self._serialize_val(val, nodes_dict, relationships_list)
                        records.append(record_dict)

                    return {
                        "status": "success",
                        "is_live": True,
                        "cypher": cypher,
                        "parameters": parameters,
                        "records": records,
                        "graph": {
                            "nodes": list(nodes_dict.values()),
                            "relationships": relationships_list
                        }
                    }
            except Exception as e:
                logger.error(f"Cypher execution error: {traceback.format_exc()}")
                return {
                    "status": "error",
                    "error": str(e),
                    "is_live": True,
                    "cypher": cypher
                }
        else:
            # Execute via Mock Engine
            return self._mock_query_engine(cypher, parameters)

    def _serialize_val(self, val: Any, nodes_dict: dict, rels_list: list) -> Any:
        """Serializes Neo4j record items into JSON serializable structures."""
        if hasattr(val, "labels") and hasattr(val, "items"):  # Neo4j Node
            node_id = str(val.element_id if hasattr(val, "element_id") else val.id)
            props = dict(val.items())
            props["id"] = props.get("id", node_id)
            props["label"] = list(val.labels)[0] if val.labels else "Node"
            nodes_dict[props["id"]] = props
            return props
        elif hasattr(val, "type") and hasattr(val, "start_node"):  # Neo4j Relationship
            rel_data = {
                "source": str(val.start_node.element_id if hasattr(val.start_node, "element_id") else val.start_node.id),
                "target": str(val.end_node.element_id if hasattr(val.end_node, "element_id") else val.end_node.id),
                "type": val.type,
                "properties": dict(val.items())
            }
            rels_list.append(rel_data)
            return rel_data
        elif isinstance(val, list):
            return [self._serialize_val(item, nodes_dict, rels_list) for item in val]
        elif isinstance(val, dict):
            return {k: self._serialize_val(v, nodes_dict, rels_list) for k, v in val.items()}
        return val

    def _mock_query_engine(self, cypher: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Provides realistic graph responses when running locally without CognoDB Cloud credentials."""
        cypher_upper = cypher.upper()
        
        nodes = list(MOCK_NODES)
        relationships = list(MOCK_RELATIONSHIPS)

        # Multi-hop Blast Radius Simulation
        if "DISRUPTION_BLAST_RADIUS" in cypher_upper or "DISRUPTIONEVENT" in cypher_upper or "AFFECTS_REGION" in cypher_upper:
            disruption_id = parameters.get("disruption_id", "DISR-701")
            disruption_node = next((n for n in nodes if n["id"] == disruption_id or n["name"] == disruption_id), nodes[-3])
            
            # Find downstream target regions/facilities
            target_ids = [r["target"] for r in relationships if r["source"] == disruption_node["id"]]
            
            # Traversal downstream: Facility -> Supplier -> Component -> Assembly -> Product
            path_nodes = [disruption_node]
            affected_suppliers = [n for n in nodes if n["id"] in ["SUPP-401", "SUPP-402"]]
            affected_components = [n for n in nodes if n["id"] in ["COMP-301", "COMP-305"]]
            affected_assemblies = [n for n in nodes if n["id"] in ["ASSY-201", "ASSY-204"]]
            affected_products = [n for n in nodes if n["id"] in ["PROD-101", "PROD-104"]]

            all_affected = path_nodes + affected_suppliers + affected_components + affected_assemblies + affected_products

            return {
                "status": "success",
                "is_live": False,
                "cypher": cypher,
                "parameters": parameters,
                "records": [
                    {
                        "disruption": disruption_node["name"],
                        "severity": disruption_node.get("severity", "HIGH"),
                        "hops": 4,
                        "affected_products": [p["name"] for p in affected_products],
                        "revenue_impact_m": sum(p["quarterly_revenue_m"] for p in affected_products)
                    }
                ],
                "graph": {
                    "nodes": all_affected,
                    "relationships": [r for r in relationships if any(r["source"] == n["id"] for n in all_affected) and any(r["target"] == n["id"] for n in all_affected)]
                }
            }

        # Single Point of Failure
        elif "SINGLE_POINTS_OF_FAILURE" in cypher_upper or "SOLE_SUPPLIER" in cypher_upper or "SOLE_SOURCE" in cypher_upper:
            spof_records = [
                {
                    "component_id": "COMP-301",
                    "component_name": "3nm SiC Power MOSFET",
                    "category": "Semiconductors",
                    "sole_supplier": "Taiwan Semi Foundry (TSMC)",
                    "sole_supplier_id": "SUPP-401",
                    "affected_products": ["QuantumDrive Server X"],
                    "product_count": 1,
                    "revenue_at_risk_m": 42.5
                },
                {
                    "component_id": "COMP-303",
                    "component_name": "Gallium Nitride Transceiver IC",
                    "category": "Semiconductors",
                    "sole_supplier": "Infineon Technologies",
                    "sole_supplier_id": "SUPP-404",
                    "affected_products": ["AeroX Jet Turbine ECU"],
                    "product_count": 1,
                    "revenue_at_risk_m": 65.2
                },
                {
                    "component_id": "COMP-305",
                    "component_name": "FPGA Cryptographic Unit",
                    "category": "Chips",
                    "sole_supplier": "Taiwan Semi Foundry (TSMC)",
                    "sole_supplier_id": "SUPP-401",
                    "affected_products": ["QuantumDrive Server X", "Nexus 6G Edge Router"],
                    "product_count": 2,
                    "revenue_at_risk_m": 73.5
                }
            ]
            return {
                "status": "success",
                "is_live": False,
                "cypher": cypher,
                "parameters": parameters,
                "records": spof_records,
                "graph": {
                    "nodes": [n for n in nodes if n["label"] in ["Component", "Supplier", "Product"]],
                    "relationships": [r for r in relationships if r["type"] in ["SUPPLIED_BY", "REQUIRES_ASSEMBLY", "USES_COMPONENT"]]
                }
            }

        # Alternate Suppliers
        elif "ALTERNATIVE_FOR" in cypher_upper or "ALTERNATE" in cypher_upper:
            supplier_id = parameters.get("supplier_id", "SUPP-401")
            alt_records = [
                {
                    "component": "3nm SiC Power MOSFET",
                    "primary_supplier": "Taiwan Semi Foundry (TSMC)",
                    "alt_supplier_id": "SUPP-405",
                    "alt_supplier": "GlobalFoundries Dresden",
                    "alt_rating": 4.4,
                    "lead_time_days": 50,
                    "switching_days": 14,
                    "extra_cost_pct": 12.5
                },
                {
                    "component": "3nm SiC Power MOSFET",
                    "primary_supplier": "Taiwan Semi Foundry (TSMC)",
                    "alt_supplier_id": "SUPP-406",
                    "alt_supplier": "Samsung Electronics Semiconductor",
                    "alt_rating": 4.8,
                    "lead_time_days": 40,
                    "switching_days": 21,
                    "extra_cost_pct": 8.0
                }
            ]
            return {
                "status": "success",
                "is_live": False,
                "cypher": cypher,
                "parameters": parameters,
                "records": alt_records,
                "graph": {
                    "nodes": [n for n in nodes if n["id"] in ["SUPP-401", "SUPP-405", "SUPP-406", "COMP-301"]],
                    "relationships": [r for r in relationships if r["source"] in ["SUPP-405", "SUPP-406", "COMP-301"]]
                }
            }

        # REQUIRES_ASSEMBLY / Default sample console queries
        elif "REQUIRES_ASSEMBLY" in cypher_upper:
            req_rels = [r for r in relationships if r["type"] == "REQUIRES_ASSEMBLY"]
            req_records = []
            rel_nodes = []
            node_map = {n["id"]: n for n in nodes}
            for r in req_rels:
                p_node = node_map.get(r["source"])
                a_node = node_map.get(r["target"])
                if p_node and a_node:
                    req_records.append({
                        "Product": p_node["name"],
                        "Assembly": a_node["name"],
                        "Quantity": r.get("quantity", 1)
                    })
                    rel_nodes.extend([p_node, a_node])
            
            unique_nodes = list({n["id"]: n for n in rel_nodes}.values())
            return {
                "status": "success",
                "is_live": False,
                "cypher": cypher,
                "parameters": parameters,
                "records": req_records,
                "graph": {
                    "nodes": unique_nodes,
                    "relationships": req_rels
                }
            }

        # Dynamic label matching for queries like MATCH (n:Supplier) or MATCH (c:Component)
        import re
        label_match = re.search(r":([A-Za-z0-9_]+)", cypher)
        if label_match:
            target_label = label_match.group(1)
            matching_nodes = [n for n in nodes if n.get("label", "").lower() == target_label.lower()]
            if matching_nodes:
                records = [{k: v for k, v in n.items()} for n in matching_nodes]
                matching_ids = set(n["id"] for n in matching_nodes)
                matching_rels = [r for r in relationships if r["source"] in matching_ids or r["target"] in matching_ids]

                return {
                    "status": "success",
                    "is_live": False,
                    "cypher": cypher,
                    "parameters": parameters,
                    "records": records,
                    "graph": {
                        "nodes": matching_nodes,
                        "relationships": matching_rels
                    }
                }

        # Default Graph Overview
        return {
            "status": "success",
            "is_live": False,
            "cypher": cypher,
            "parameters": parameters,
            "records": [{"node_count": len(nodes), "edge_count": len(relationships)}],
            "graph": {
                "nodes": nodes,
                "relationships": relationships
            }
        }

    def close(self):
        if self._driver:
            self._driver.close()

db_manager = CognoDBManager()
