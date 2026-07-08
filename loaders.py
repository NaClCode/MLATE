import pandas as pd
from pathlib import Path
from .logger import logger

class BaseLoader:
    """Base class for data loaders."""
    
    # Common column mappings for different sources
    MAPPINGS = {
        "wos": {
            "title": ["TI", "Article Title", "Title"],
            "abstract": ["AB", "Abstract"],
            "keywords": ["DE", "Author Keywords", "ID", "Keywords Plus", "Keywords"]
        },
        "scopus": {
            "title": ["Title"],
            "abstract": ["Abstract"],
            "keywords": ["Author Keywords", "Index Keywords"]
        },
        "standard": {
            "title": ["Title", "题目", "标题"],
            "abstract": ["Abstract", "摘要"],
            "keywords": ["Keywords", "Author Keywords", "关键词"]
        }
    }

    @staticmethod
    def load(file_path: str, source_type: str = "auto") -> tuple[pd.DataFrame, dict]:
        """Load literature data and return (df, mapping)."""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        # 1. Load the raw data
        try:
            if ext == ".csv":
                df = pd.read_csv(file_path, encoding="utf-8-sig")
            elif ext in [".xls", ".xlsx"]:
                df = pd.read_excel(file_path)
            elif ext in [".txt", ".tsv"]:
                df = pd.read_csv(file_path, sep="\t", encoding="utf-8-sig")
            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            raise

        # 2. Adaptive column mapping (without renaming)
        return BaseLoader.identify_columns(df, source_type)

    @staticmethod
    def identify_columns(df: pd.DataFrame, source_type: str = "auto") -> tuple[pd.DataFrame, dict]:
        """Identify key columns and return (df_cleaned, mapping)."""
        # Deduplicate columns first
        df = df.loc[:, ~df.columns.duplicated()]
        columns = df.columns.tolist()
        
        mapping_to_use = {}
        if source_type != "auto" and source_type in BaseLoader.MAPPINGS:
            mapping_to_use = BaseLoader.MAPPINGS[source_type]
        else:
            best_score = -1
            best_source = "standard"
            for src, maps in BaseLoader.MAPPINGS.items():
                score = sum(1 for target_list in maps.values() 
                           for col in target_list if col in columns)
                if score > best_score:
                    best_score = score
                    best_source = src
            mapping_to_use = BaseLoader.MAPPINGS[best_source]
            logger.info(f"Detected source type: {best_source}")

        # Final mapping of original column names
        res_mapping = {"title": "Title", "abstract": "Abstract", "keywords": "Keywords"}
        found = {"title": False, "abstract": False, "keywords": False}
        
        # 1. Try predefined mappings
        for internal_name, candidates in mapping_to_use.items():
            for cand in candidates:
                if cand in columns:
                    res_mapping[internal_name] = cand
                    found[internal_name] = True
                    break
        
        # 2. Heuristic fallback
        if not found["title"]:
            for col in columns:
                if any(kw in col.lower() for kw in ["title", "ti"]):
                    res_mapping["title"] = col
                    found["title"] = True
                    break
                    
        if not found["abstract"]:
            for col in columns:
                if any(kw in col.lower() for kw in ["abstract", "ab", "summary"]):
                    res_mapping["abstract"] = col
                    found["abstract"] = True
                    break

        if not found["title"]:
            logger.warning("Could not find Title column automatically.")
        
        # Log the identified mappings
        logger.section("列名映射确认", "Column Mapping Confirmation")
        logger.info(f"  题目 (Title)    : {res_mapping['title']}")
        logger.info(f"  摘要 (Abstract) : {res_mapping['abstract']}")
        logger.info(f"  关键词 (Keywords): {res_mapping['keywords']}")
            
        return df, res_mapping
