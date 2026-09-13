""" Script to save numpy arrays in gwyddion file format.
Copyright Nanosurf AG 2023
License - MIT
"""

import datetime as datetime
from dataclasses import dataclass
import numpy as np
import struct
import logging
logger = logging.getLogger(__name__)
import pathlib

@dataclass
class GwySizeInfo:
    x_range: float
    y_range: float
    x_offset: float = 0.0
    y_offset: float = 0.0
    unit_xy: str = "m"

class GwyComponent:
    def __init__(self, id: str, name:str, value) -> None:
        self.name = name
        self.id = id
        self.value = value
        self.data_converter = {
            's' : self._write_str,
            'i' : self._write_int,
            'o' : self._write_obj,
            'd' : self._write_double,
            'b' : self._write_byte,
            'D' : self._write_double_array
        } 
    
    def get_byte_stream(self) -> bytearray:
        data_stream = bytearray(f"{self.name}\0{self.id}".encode('utf-8'))
        data_stream += self.data_converter[self.id](self.value)
        return data_stream

    def _write_str(self,value:str) -> bytearray:
        return bytearray(f"{value}\0".encode('utf-8'))

    def _write_int(self,value:int):
        return bytearray(int(value).to_bytes(4, byteorder='little'))

    def _write_obj(self,value:'GwyComponent'):
        return value.get_byte_stream()

    def _write_double(self,value:float):
        return bytearray(struct.pack("d", value))

    def _write_byte(self, value:int):
        return bytearray(int(value).to_bytes(2, byteorder='little'))

    def _write_double_array(self,value:list[float]):
        data_stream = bytearray(len(value).to_bytes(4, byteorder='little'))
        data_stream += bytearray(struct.pack('{}d'.format(len(value)), *value)) 
        return data_stream

class GwyContainer:
    def __init__(self, name:str) -> None:
        self.name = name
        self._components:list[GwyComponent] = []

    def add(self, new_comp:GwyComponent):
        self._components.append(new_comp)

    def _get_component_stream(self)-> int:
        component_stream = bytearray()
        for c in self._components:
            component_stream += c.get_byte_stream()
        return component_stream

    def get_byte_stream(self) -> bytearray:
        data_header = bytearray(f"{self.name}\0".encode('utf-8'))
        data_stream = self._get_component_stream()
        data_size = bytearray(len(data_stream).to_bytes(4, byteorder='little'))
        return data_header + data_size + data_stream

class GwyFile:
    def __init__(self, file_name:str = None) -> None:
        self.file_name = file_name
        self.top_container = GwyContainer("GwyContainer")

    def save(self, file_name:pathlib.Path = None) -> bool:
        done = False

        if file_name is None and self.file_name is None:
            raise ValueError("No file name was given. Neither in constructor nor as parameter") 
        if file_name is not None: gwy_file_path = pathlib.Path(file_name)
        else:                     gwy_file_path = pathlib.Path(self.file_name)

        try:
            gwy_file = open(gwy_file_path,'wb')
            gwy_file.write('GWYP'.encode('utf-8'))
            gwy_file.write(self.top_container.get_byte_stream())
            gwy_file.close()
            done = True
        except Exception as e:
            logger.info(e)
            done = False
        return done

def _get_date_time_now():
    now = datetime.datetime.now()
    date_time_str = "{:4d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
    # 2021-07-27 19:18:12
    return date_time_str


def savedata_gwy(gwy_file_path:pathlib.Path, size_info:GwySizeInfo, data_sets:list[np.ndarray], data_labels:list[str], data_units:list[str], meta_data:dict = {}, time_str:str = None) -> bool:
    done = False

    # check parameters
    num_data_set = len(data_sets)
    if len(data_labels) != num_data_set:
        raise ValueError(f"Length of 'data_labels' do not match number of data sets. Got {len(data_labels)}, but need {num_data_set}")
    if len(data_units) != num_data_set:
        raise ValueError(f"Length of 'data_units' do not match number of data sets. Got {len(data_units)}, but need {num_data_set}")

    if time_str is None:
        time_str = _get_date_time_now()

    # add fix meta data information
    meta_data['file_creator'] = 'nanosurf python gwy_exporter v1.0'
    meta_data['file_date_times'] = time_str

    try:    
        # Assemble data in array
        data_sets:np.ndarray = np.dstack(tuple([d for d in data_sets]))

        s = data_sets.shape
        if len(s) > 2:
            num_channels = s[2]
        else:
            num_channels = 1

        gwy_file = GwyFile(gwy_file_path)
        for i in range(num_channels):

            image_number_of_line  = data_sets[:,:,i].shape[0]
            image_points_per_line = data_sets[:,:,i].shape[1]
            num_data_points = image_number_of_line * image_points_per_line

            x_axis = np.linspace(size_info.x_offset, size_info.x_offset + size_info.x_range, image_points_per_line)
            y_axis = np.linspace(size_info.y_offset, size_info.y_offset + size_info.y_range, image_number_of_line )

            unit_xy = GwyContainer("GwySIUnit")
            unit_xy.add(GwyComponent('s','unitstr',size_info.unit_xy))

            unit_z = GwyContainer("GwySIUnit")
            unit_z.add(GwyComponent('s','unitstr',data_units[i]))

            data_field = GwyContainer("GwyDataField")
            data_field.add(GwyComponent('i','xres',len(x_axis)))
            data_field.add(GwyComponent('i','yres',len(y_axis)))
            data_field.add(GwyComponent('d','xreal',abs(x_axis[-1]-x_axis[0])))
            data_field.add(GwyComponent('d','yreal',abs(y_axis[-1]-y_axis[0])))
            data_field.add(GwyComponent('d','xoff',x_axis[0]))
            data_field.add(GwyComponent('d','yoff',y_axis[0]))
            data_field.add(GwyComponent('o','si_unit_xy', unit_xy ))
            data_field.add(GwyComponent('o','si_unit_z', unit_z ))
            current_data = np.reshape(data_sets[:,:,i],(1, num_data_points)).flatten()
            data_field.add(GwyComponent('D','data', current_data.tolist()))
            gwy_file.top_container.add(GwyComponent('o', f'/{i}/data', data_field))
            gwy_file.top_container.add(GwyComponent("s", f"/{i}/data/title", data_labels[i]))

            # if there is a nan value, make a mask for this channel
            current_nan = np.isnan(current_data)
            if np.any(current_nan):
                mask_data_field = GwyContainer("GwyDataField")
                mask_data_field.add(GwyComponent('i','xres',len(x_axis)))
                mask_data_field.add(GwyComponent('i','yres',len(y_axis)))
                mask_data_field.add(GwyComponent('d','xreal',abs(x_axis[-1]-x_axis[0])))
                mask_data_field.add(GwyComponent('d','yreal',abs(y_axis[-1]-y_axis[0])))
                mask_data_field.add(GwyComponent('d','xoff',x_axis[0]))
                mask_data_field.add(GwyComponent('d','yoff',y_axis[0]))
                mask_data_field.add(GwyComponent('o','si_unit_xy', unit_xy ))
                mask_data_field.add(GwyComponent('o','si_unit_z', unit_z ))
                mask_data_field.add(GwyComponent('D','data', current_nan.tolist()))
                gwy_file.top_container.add(GwyComponent('o', f'/{i}/mask', mask_data_field))

            meta_container = GwyContainer('GwyContainer')
            for meta_key, meta_value in meta_data.items():
                meta_container.add(GwyComponent('s',meta_key, meta_value))

            gwy_file.top_container.add(GwyComponent("o", f"/{i}/meta", meta_container))
            
        done = gwy_file.save()  
    except Exception as e:
        logger.info(e)
        done = False
    return done

