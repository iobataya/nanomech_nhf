from unittest import result
import numpy as np
import pandas as pd
import pathlib

class FieldMap:
    """A class to manage a 2D field map of results using a pandas DataFrame.
       For example, this table contain multiple results at each point in a sweep, with one row per point.
    """
    def __init__(self, xy_point_count:int, parameters:list[str])-> None:
        self.xy_point_count = xy_point_count
        self.parameters = parameters
        self.table = pd.DataFrame(columns=["Point index"] + parameters)
        # Set Point index column as int, and set other columns as float64
        self.table = self.table.astype({"Point index": int, **{param: float for param in parameters}})
        # fill with np.nan value
        self.table = self.table.fillna(np.nan)

    def set_parameters_at(self, point_index:int, parameters:dict):
        """Update the parameters at a specific point index in the DataFrame.

        Parameters:
        - point_index: The index of the point for which results are being updated.
        - parameters: A dictionary containing the parameter values. Keys should match the DataFrame columns.
        """
        # if the point_index is not already in the DataFrame, add a new row
        if point_index not in self.table["Point index"].values:
            new_row = {"Point index": point_index}
            new_row.update(parameters)
            self.table.loc[len(self.table)] = new_row
        else:
            # Update the existing row with the new parameters
            for param, value in parameters.items():
                self.table.loc[self.table["Point index"] == point_index, param] = value

    def to_csv(self, filename:pathlib.Path|str):
        """Save the DataFrame to a CSV file."""
        self.table.to_csv(filename, index=False)


class FieldSweepTable:
    """A class to manage a 2D field sweep table of results using a pandas DataFrame.
       For example, this can contain multiple frequency-dependent results at each point in a sweep.
    """
    def __init__(self, xy_point_count:int, parameters:list[str])-> None:
        self.xy_point_count = xy_point_count
        self.parameters = parameters
        self.table = pd.DataFrame(columns=["Point index"] + parameters)
        # Set Point index column as int, and set other columns as float64
        self.table = self.table.astype({"Point index": int, **{param: float for param in parameters}})

    def set_swept_parameters_at(self, point_index:int, sweeping_param_name:str, params_array:dict):
        """Update the swept parameters at a specific point index in the DataFrame.

        Parameters:
        - point_index: The index of the point for which results are being updated.
        - sweeping_param_name: The name of the sweeping parameter (e.g., "Frequency").
        - params_array: A dictionary containing arrays of parameter values. Keys should match the DataFrame columns.
        """
        # if the point_index is not already in the DataFrame, add new rows for each value in params_array
        if point_index not in self.table["Point index"].values:
            for i in range(len(params_array[sweeping_param_name])):
                new_row = {"Point index": point_index}
                for param, values in params_array.items():
                    new_row[param] = values[i]
                self.table.loc[len(self.table)] = new_row
        else:
            # Update the existing rows with the new parameters
            for i in range(len(params_array[sweeping_param_name])):
                for param, values in params_array.items():
                    self.table.loc[(self.table["Point index"] == point_index) & (self.table[sweeping_param_name] == values[i]), param] = values[i]
    
    def to_csv(self, filename:pathlib.Path|str):
        """Save the DataFrame to a CSV file."""
        self.table.to_csv(filename, index=False)
