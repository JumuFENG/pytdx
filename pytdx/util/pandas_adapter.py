"""
自动选择 pandas 或纯Python实现数据处理功能
"""

from typing import Any, Dict, List, Optional, Union, Tuple
import importlib.util
import datetime


if importlib.util.find_spec("pandas") is None:
    import csv

    class DataFrame:
        """DataFrame适配器类"""

        def __init__(self, data: List[Dict[str, Any]],
                    columns: Optional[List[Dict[str, Any]]] = None):
            self.data = data.copy() if data else []
            self._index = IndexProxy(self.data)

        @property
        def empty(self) -> bool:
            """检查数据是否为空"""
            return len(self.data) == 0

        @property
        def columns(self) -> List[str]:
            """获取列名列表"""
            return list(self.data[0].keys()) if self.data else []

        @property
        def shape(self) -> Tuple[int, int]:
            """获取数据形状"""
            return (len(self.data), len(self.columns) if self.data else 0)
        
        @property 
        def index(self):
            """获取索引代理"""
            return self._index
        
        @index.setter
        def index(self, value):
            """设置索引"""
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # 如果是可迭代对象，创建一个默认列名存储索引
                col_name = '_index'
                for i, val in enumerate(self.data):
                    if i < len(value):
                        val[col_name] = val
                self._index._column_name = col_name

        def head(self, n: int = 5) -> 'DataFrame':
            """获取前n行数据"""
            return DataFrame(data=self.data[:n])

        def sort_values(self, by: str, ascending: bool = True) -> 'DataFrame':
            """按指定列排序"""
            if not self.data or by not in self.columns:
                return self

            sorted_data = sorted(self.data, key=lambda x: x.get(by, 0), reverse=not ascending)
            return DataFrame(data=sorted_data)

        def to_csv(self, filepath: str, index: bool = False, encoding: str = 'utf-8') -> None:
            """保存为CSV文件"""
            if not self.data:
                return

            fieldnames = self.columns
            with open(filepath, 'w', newline='', encoding=encoding) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not index:
                    writer.writeheader()
                writer.writerows(self.data)

        def to_excel(self, filepath: str, index: bool = False) -> None:
            """保存为Excel文件（需要openpyxl库）"""
            if not self.data:
                return
            try:
                from openpyxl import Workbook
            except ImportError:
                raise ImportError("请安装 openpyxl 库以支持 Excel 导出: pip install openpyxl")

            wb = Workbook()
            ws = wb.active
            if not index:
                ws.append(self.columns)
            for row in self.data:
                ws.append([row.get(col, '') for col in self.columns])
            wb.save(filepath)

        def to_dict(self, orient: str = 'records') -> Union[List[Dict], Dict]:
            """转换为字典格式"""
            if orient == 'records':
                return self.data
            elif orient == 'dict':
                result = {}
                for col in self.columns:
                    result[col] = [row.get(col) for row in self.data]
                return result
            else:
                raise ValueError(f"不支持的orient参数: {orient}")

        def __len__(self) -> int:
            """返回数据行数"""
            return len(self.data)

        def __iter__(self):
            """支持迭代"""
            return iter(self.data)
        
        def __repr__(self) -> str:
            """字符串表示"""
            if self.empty:
                return "DataFrame(empty)"
            
            preview = []
            for i, row in enumerate(self.data[:5]):
                preview.append(str(row))
            preview_str = ",\n  ".join(preview)
            if len(self.data) > 5:
                preview_str += f"\n  ... (共 {len(self.data)} 行)"
            return f"DataFrame([\n  {preview_str}\n])"

        def rename(self, columns: Dict[str, str]) -> 'DataFrame':
            """重命名列"""
            return DataFrame(data=[{columns.get(col, col): value for col, value in row.items()} for row in self.data])

        def assign(self, **kwargs) -> 'DataFrame':
            """添加或修改列"""
            new_data = []
            for row in self.data:
                new_row = row.copy()
                for key, value in kwargs.items():
                    if callable(value):
                        new_row[key] = value(new_row)
                    else:
                        new_row[key] = value
                new_data.append(new_row)
            return DataFrame(data=new_data)

        def set_index(self, column_name: str, drop: bool = False, inplace: bool = False) -> 'DataFrame':
            """设置索引"""
            if inplace:
                self._index._column_name = column_name if not drop else None
                return self
            else:
                new_df = DataFrame(data=self.data)
                new_df._index._column_name = column_name if not drop else None
                return new_df
        
        def drop(self, columns, axis: int = 1, inplace: bool = False) -> 'DataFrame':
            """删除列"""
            if axis == 0:
                # 按行删除（不支持）
                return self if not inplace else None
            
            if isinstance(columns, str):
                columns = [columns]
            
            if inplace:
                for row in self.data:
                    for col in columns:
                        if col in row:
                            del row[col]
                return self
            else:
                new_data = []
                for row in self.data:
                    new_row = row.copy()
                    for col in columns:
                        if col in new_row:
                            del new_row[col]
                    new_data.append(new_row)
                return DataFrame(data=new_data)
        
        def __getitem__(self, key):
            """支持列访问和切片"""
            if isinstance(key, str):
                return [row.get(key) for row in self.data]
            elif isinstance(key, slice):
                return DataFrame(data=self.data[key])
            elif isinstance(key, list):
                return DataFrame(data=[{col: row[col] for col in key} for row in self.data])
            elif isinstance(key, tuple) and len(key) == 2:
                # 支持行和列的双重索引
                rows, cols = key
                if isinstance(rows, slice):
                    selected_data = self.data[rows]
                elif isinstance(rows, list):
                    selected_data = [self.data[i] if i < len(self.data) else None for i in rows]
                else:
                    selected_data = [self.data[rows]]
                
                if isinstance(cols, str):
                    return [row.get(cols) for row in selected_data]
                elif isinstance(cols, list):
                    return [{col: row.get(col) for col in cols} for row in selected_data]
            else:
                raise KeyError(f"不支持的key类型: {type(key)}")

    def concat(dfs: List[DataFrame]) -> DataFrame:
        """连接多个DataFrame"""
        combined_data = []
        for df in dfs:
            combined_data.extend(df.data)
        return DataFrame(data=combined_data)
    
    def to_datetime(data, format: str = None) -> List:
        """将数据转换为datetime格式"""
        if isinstance(data, (list, tuple)):
            return [to_datetime(item, format) for item in data]
        elif isinstance(data, str):
            try:
                if format:
                    return datetime.datetime.strptime(data, format)
                else:
                    # 尝试常见格式
                    for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y%m%d']:
                        try:
                            return datetime.datetime.strptime(data, fmt)
                        except ValueError:
                            continue
                    raise ValueError(f"无法解析日期格式: {data}")
            except Exception as e:
                raise ValueError(f"日期转换失败: {e}")
        else:
            return data
    
    def set_option(option: str, value: Any) -> None:
        """设置pandas选项（无pandas版本为空实现）"""
        # 在无pandas版本中，这些设置不影响输出
        pass
    
    # 添加索引相关功能
    class IndexProxy:
        """索引代理类，模拟pandas的索引功能"""
        def __init__(self, data: List[Dict], column_name: str = None):
            self.data = data
            self._column_name = column_name
            
        def __setitem__(self, key, values):
            """设置索引"""
            if isinstance(key, str):
                self._column_name = key
                if isinstance(values, (list, tuple)):
                    for i, row in enumerate(self.data):
                        if i < len(values):
                            row[key] = values[i]
        
        def __getattr__(self, name):
            """代理其他属性访问"""
            if name in ['name', 'names']:
                return self._column_name
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            
        def __repr__(self):
            return f"IndexProxy(column='{self._column_name}')"

else:
    import pandas as pd
    DataFrame = pd.DataFrame

    def concat(dfs: List[DataFrame]) -> DataFrame:
        """连接多个DataFrame"""
        return pd.concat(dfs, ignore_index=True)
    
    def to_datetime(data, format: str = None):
        """将数据转换为datetime格式"""
        return pd.to_datetime(data, format=format)
    
    def set_option(option: str, value: Any) -> None:
        """设置pandas选项"""
        return pd.set_option(option, value)

