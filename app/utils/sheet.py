#%%
import pandas as pd
from pandas._typing import Axes, Dtype
import os
import numpy as np
from pathlib import Path
from typing import Union

class Sheet:
    def __init__(self, 
            excel_file_path:Union[str, Path], 
            sheet_name:str=None, 
            default_data:dict=None, 
            index:Axes=None,
            conlumns:Axes=None, 
            dtype:np.dtype=None, 
            clear:bool=False
            ):
        
        self.excel_file_path = Path(excel_file_path)
        self.sheet_name = sheet_name
        if (default_data or conlumns) and \
           (clear or not self.excel_file_path.exists()):
            if sheet_name is None:
                self.sheet_name = 'Sheet1'
            self.dataframe = pd.DataFrame(data=default_data, index=index, columns=conlumns, dtype=dtype)
        else:
            try:
                with pd.ExcelFile(self.excel_file_path) as excel_file:
                    sheet_names = excel_file.sheet_names
                    for name in sheet_names:
                        if sheet_name is not None and name != sheet_name:
                            continue
                        df = excel_file.parse(name)
                        self.dataframe = df
                        self.sheet_name = name
                        break
            except FileNotFoundError:
                raise FileNotFoundError(f"File '{excel_file_path}' not found")
            except Exception as e:
                raise Exception(f"Error reading file '{excel_file_path}': {e}")
    
    def __len__(self):
        return self.dataframe.shape[0]

    def __iter__(self):
        for i in range(self.dataframe.shape[0]):
            yield self.dataframe.loc[i]
    
    def __getitem__(self, indices):
        return self.dataframe.loc[indices]
    
    def __setitem__(self, indices, value):
        self.dataframe.loc[indices] = value

    def __contains__(self, key):
        return key in self.dataframe.index

    def append(self, value):
        self[len(self)] = value

    def column_names(self):
        return list(self.dataframe.columns)
    
    def save(self, index:bool=False):
        dirname = Path(self.excel_file_path).parent
        if not dirname.exists():
            dirname.mkdir(parents=True)
        self.dataframe.to_excel(self.excel_file_path, sheet_name=self.sheet_name, index=index)

if __name__ == "__main__":
    from app.utils.paths import PATH_LESSONS

    # read exsisting excel file
    data_sheet = Sheet(PATH_LESSONS / 'test.xlsx')
    print(data_sheet.column_names())
    print(data_sheet[0, "EN"])
    print(data_sheet[0])
    
    # create new excel file
    data_sheet = Sheet(PATH_LESSONS / 'test1.xlsx', default_data={'EN':[], 'CN':[], 'ID':[]}, dtype=str)
    data_sheet[0, "EN"] = "hello"
    data_sheet[0, "CN"] = "你好"
    data_sheet[0, "ID"] = "halo"
    print(data_sheet[0])
    data_sheet.save()