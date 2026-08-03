import pandas as pd
import numpy as np
import io
import os
import json
from django.conf import settings as django_settings

GROQ_API_KEY = django_settings.GROQ_API_KEY
GROQ_MODEL   = django_settings.GROQ_MODEL

class PandasAgent:
    def __init__(self):
        try:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY, timeout=30.0)
        except Exception:
            self.groq_client = None

    def get_schema(self, file_path, file_type):
        """Read top 3 rows to show schema to LLM."""
        try:
            if not os.path.exists(file_path):
                return None, None
            
            if file_type == 'csv':
                df = pd.read_csv(file_path)
            elif file_type == 'excel':
                df = pd.read_excel(file_path)
            else:
                return None, None
            
            # Get string representation of top 3 rows
            head_str = df.head(3).to_markdown()
            return df, head_str
        except Exception:
            return None, None

    def generate_code(self, question, schemas_text):
        """Ask LLM to write pandas code."""
        prompt = f"""
You are an expert Data Analyst using Pandas. 
You are given the following DataFrames loaded in memory. Their names and top 3 rows are:
{schemas_text}

Write a PURE PYTHON script using pandas to answer the user's question.
1. The DataFrames (e.g. df_0, df_1) are ALREADY loaded. DO NOT use pd.read_csv or pd.read_excel.
2. DO NOT import any dangerous modules (no os, sys, subprocess). You can use pandas (as pd) and numpy (as np).
3. At the end of your script, you MUST assign the final answer to a variable named `result`.
4. Return ONLY the raw Python code, no markdown backticks, no explanations. Just the code.

User's Question: {question}
"""
        try:
            response = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=500,
            )
            code = response.choices[0].message.content.strip()
            # Clean up markdown if LLM disobeyed
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            return code.strip()
        except Exception as e:
            return None

    def execute_code(self, code, df_dict):
        """Execute sandboxed python code."""
        # Security Validation against RCE and Sandbox Escapes
        import re
        forbidden_patterns = [
            r'__class__', r'__mro__', r'__subclasses__', r'__globals__', r'__builtins__', r'__getattribute__',
            r'\bimport\b', r'__import__', r'eval\(', r'exec\(', r'open\(', r'os\.', r'sys\.', r'subprocess'
        ]
        for pattern in forbidden_patterns:
            if re.search(pattern, code):
                return None, "Blocked due to security policy (forbidden keywords detected)."

        safe_globals = {
            '__builtins__': {
                'len': len, 'sum': sum, 'min': min, 'max': max, 'abs': abs,
                'round': round, 'int': int, 'float': float, 'str': str,
                'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
                'bool': bool, 'Exception': Exception,
                'print': print,
            },
            'pd': pd,
            'np': np,
        }
        safe_globals.update(df_dict)
        local_env = {}
        try:
            exec(code, safe_globals, local_env)
            return local_env.get('result', None), None
        except Exception as e:
            return None, str(e)

    def analyze(self, question, data_files):
        """Main entry point."""
        if not self.groq_client or not data_files:
            return None

        df_dict = {}
        schemas_text = ""
        
        for i, df_obj in enumerate(data_files):
            df, schema = self.get_schema(df_obj.file.path, df_obj.file_type)
            if df is not None:
                df_name = f"df_{i}"
                df_dict[df_name] = df
                schemas_text += f"\nDataFrame Name: {df_name}\n"
                schemas_text += f"Original File Name: {os.path.basename(df_obj.file.name)}\n"
                schemas_text += f"Columns and sample data:\n{schema}\n"

        if not df_dict:
            return None

        # 1. Generate Code
        code = self.generate_code(question, schemas_text)
        if not code:
            return None

        # 2. Execute Code
        result, err = self.execute_code(code, df_dict)
        
        if err:
            print(f"Pandas execution error: {err}")
            return None
        
        # 3. Final Synthesis (Translation to Arabic and formatting)
        if result is not None:
            synth_prompt = f"""
You are an expert Data Analytics Assistant for an ERP platform.
You just queried the database using Pandas and got this result: {str(result)}

Answer the user's question clearly, accurately, and in professional Arabic.
1. Never guess or hallucinate. Use ONLY the result provided.
2. If the result is a dataframe or list, format it cleanly with bullet points or a short table.
3. If the result is empty or indicates not found, state clearly in Arabic that the requested data does not exist in the uploaded files.

User's Question: {question}
"""
            try:
                response = self.groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": synth_prompt}],
                    temperature=0.1,
                    max_tokens=1000,
                )
                return response.choices[0].message.content
            except Exception:
                return str(result) # Fallback to raw result
                
        return None
