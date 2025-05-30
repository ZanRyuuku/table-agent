import os
import pandas as pd
import numpy as np
import logging
from fastapi import UploadFile
from pathlib import Path
import aiofiles
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("file_service")

# 获取根目录位置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_upload_file(file: UploadFile, file_id: str, file_extension: str) -> str:
    """保存上传的文件到指定目录"""
    saved_file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_extension}")
    
    async with aiofiles.open(saved_file_path, 'wb') as out_file:
        # 读取上传的文件内容并写入目标文件
        content = await file.read()
        await out_file.write(content)
    
    logger.info(f"文件已保存: {saved_file_path}")
    return saved_file_path

async def read_file_preview(file_id: str, rows: int = 20) -> Dict[str, Any]:
    """读取文件预览内容"""
    # 查找匹配的文件
    file_path = None
    for ext in ['.csv', '.xlsx', '.xls']:
        potential_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
        if os.path.exists(potential_path):
            file_path = potential_path
            break
    
    if not file_path:
        raise FileNotFoundError(f"找不到ID为 {file_id} 的文件")
    
    # 根据文件类型读取数据
    file_type = Path(file_path).suffix.lower()
    try:
        if file_type == '.csv':
            df = pd.read_csv(file_path, keep_default_na=True)
        else:  # .xlsx 或 .xls
            df = pd.read_excel(file_path, keep_default_na=True)
    
        # 统一处理所有类型的空值、无穷值和NaN值
        df = df.replace([float('inf'), float('-inf'), np.inf, -np.inf], None)
        
        # 将所有NaN、None和pd.NA替换为None
        df = df.astype(object).replace([pd.NA, pd.NaT, np.nan], None)
        df = df.where(pd.notnull(df), None)
        
        logger.info(f"文件 {file_id} 数据处理完成，行数: {len(df)}, 列数: {len(df.columns)}")
        
        # 构建预览数据
        preview_data = {
            "columns": df.columns.tolist(),
            "data": df.head(rows).to_dict(orient="records"),
            "rows_count": len(df),
            "file_type": file_type[1:]  # 去掉点号
        }
        
        return preview_data
    except Exception as e:
        logger.error(f"处理文件 {file_id} 时发生错误: {str(e)}")
        raise Exception(f"读取文件失败: {str(e)}")

async def get_file_path_by_id(file_id: str) -> Optional[str]:
    """通过文件ID查找文件路径"""
    for ext in ['.csv', '.xlsx', '.xls']:
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
        if os.path.exists(file_path):
            return file_path
    return None

async def export_file(file_id: str, filename: Optional[str] = None) -> str:
    """导出处理后的文件"""
    # 查找原始文件的路径
    original_file_path = await get_file_path_by_id(file_id)
    if not original_file_path:
        raise FileNotFoundError(f"找不到ID为 {file_id} 的文件")
    
    # 查找处理后的文件
    processed_path = os.path.join(UPLOAD_DIR, f"{file_id}_processed{Path(original_file_path).suffix}")
    
    # 如果没有处理后的文件，返回原始文件
    if not os.path.exists(processed_path):
        return original_file_path
    
    return processed_path 