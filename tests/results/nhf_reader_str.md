# A forcecurve
## By str(nhf_reader)
```
Measurement 'Spec Grid 8' of type 'Spectroscopy':
    Segment 'Advance to Setpoint 1':
        Channel 'Deflection':
        Channel 'Position Z':
        Channel 'Z-Controller In':
        Channel 'Z-Controller PID Out':
        Channel 'Sampler Meta Channel':
        Channel 'Sampler Timestamp':
        Channel 'Time':
        Dataset '/group_0000/subgroup_0000/dataset_0001':
        Dataset '/group_0000/subgroup_0000/dataset_0003':
        Dataset '/group_0000/subgroup_0000/dataset_0005':
        Dataset '/group_0000/subgroup_0000/dataset_0007':
        Dataset '/group_0000/subgroup_0000/dataset_0009':
        Dataset '/group_0000/subgroup_0000/dataset_0011':
        Dataset '/group_0000/subgroup_0000/dataset_0013':
    Segment 'Retract 1':
        Channel 'Deflection':
        Channel 'Position Z':
        Channel 'Z-Controller In':
        Channel 'Z-Controller PID Out':
        Channel 'Sampler Meta Channel':
        Channel 'Sampler Timestamp':
        Channel 'Time':
        Dataset '/group_0000/subgroup_0001/dataset_0001':
        Dataset '/group_0000/subgroup_0001/dataset_0003':
        Dataset '/group_0000/subgroup_0001/dataset_0005':
        Dataset '/group_0000/subgroup_0001/dataset_0007':
        Dataset '/group_0000/subgroup_0001/dataset_0009':
        Dataset '/group_0000/subgroup_0001/dataset_0011':
        Dataset '/group_0000/subgroup_0001/dataset_0013':
    Channel '':
    Channel '':
Calibration Group 'group_0001':
```

## By summary_nhf_measurement method in nm_io.py

```
Nanosurf Studio v16.10-3e61df74b7
# channel  ['coordinates_x', 'coordinates_y']
     coordinates_x (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): , shape: (1,), unit: 
     coordinates_y (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): , shape: (1,), unit: 
# segment: ['Advance to Setpoint 1', 'Retract 1']
     Advance to Setpoint 1 (<class 'nanosurf.lib.util.nhf_reader.NHFSegment'>):
        Channels: ['Deflection', 'Position Z', 'Z-Controller In', 'Z-Controller PID Out', 'Sampler Meta Channel', 'Sampler Timestamp', 'Time']
             Deflection (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Deflection, shape: (1722,), unit: V
             Position Z (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Position Z, shape: (1722,), unit: m
             Z-Controller In (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Z-Controller In, shape: (1722,), unit: V
             Z-Controller PID Out (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Z-Controller PID Out, shape: (1722,), unit: m
             Sampler Meta Channel (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Sampler Meta Channel, shape: (1722,), unit: int
             Sampler Timestamp (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Sampler Timestamp, shape: (1722,), unit: int
             Time (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Time, shape: (1722,), unit: s
     Retract 1 (<class 'nanosurf.lib.util.nhf_reader.NHFSegment'>):
        Channels: ['Deflection', 'Position Z', 'Z-Controller In', 'Z-Controller PID Out', 'Sampler Meta Channel', 'Sampler Timestamp', 'Time']
             Deflection (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Deflection, shape: (2065,), unit: V
             Position Z (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Position Z, shape: (2065,), unit: m
             Z-Controller In (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Z-Controller In, shape: (2065,), unit: V
             Z-Controller PID Out (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Z-Controller PID Out, shape: (2065,), unit: m
             Sampler Meta Channel (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Sampler Meta Channel, shape: (2065,), unit: int
             Sampler Timestamp (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Sampler Timestamp, shape: (2065,), unit: int
             Time (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Time, shape: (2065,), unit: s
```

# Forcemapping
## By str(nhf_reader)
```
Measurement 'Spec Grid 28' of type 'Spectroscopy':
    Segment 'Advance to Setpoint 1':
        Channel 'Topography':
        Channel 'Z-Controller In':
        Channel 'Deflection':
        Channel 'Position Z':
        Channel 'Position X':
        Channel 'Position Y':
        Channel 'X-Controller Out':
        Channel 'Y-Controller Out':
        Channel 'Sampler Meta Channel':
        Channel 'Sampler Timestamp':
        Channel 'Time':
        Dataset '/group_0000/subgroup_0000/dataset_0001':
        Dataset '/group_0000/subgroup_0000/dataset_0003':
        Dataset '/group_0000/subgroup_0000/dataset_0005':
        Dataset '/group_0000/subgroup_0000/dataset_0007':
        Dataset '/group_0000/subgroup_0000/dataset_0009':
        Dataset '/group_0000/subgroup_0000/dataset_0011':
        Dataset '/group_0000/subgroup_0000/dataset_0013':
        Dataset '/group_0000/subgroup_0000/dataset_0015':
        Dataset '/group_0000/subgroup_0000/dataset_0017':
        Dataset '/group_0000/subgroup_0000/dataset_0019':
        Dataset '/group_0000/subgroup_0000/dataset_0021':
    Segment 'Retract 1':
        Channel 'Topography':
        Channel 'Z-Controller In':
        Channel 'Deflection':
        Channel 'Position Z':
        Channel 'Position X':
        Channel 'Position Y':
        Channel 'X-Controller Out':
        Channel 'Y-Controller Out':
        Channel 'Sampler Meta Channel':
        Channel 'Sampler Timestamp':
        Channel 'Time':
        Dataset '/group_0000/subgroup_0001/dataset_0001':
        Dataset '/group_0000/subgroup_0001/dataset_0003':
        Dataset '/group_0000/subgroup_0001/dataset_0005':
        Dataset '/group_0000/subgroup_0001/dataset_0007':
        Dataset '/group_0000/subgroup_0001/dataset_0009':
        Dataset '/group_0000/subgroup_0001/dataset_0011':
        Dataset '/group_0000/subgroup_0001/dataset_0013':
        Dataset '/group_0000/subgroup_0001/dataset_0015':
        Dataset '/group_0000/subgroup_0001/dataset_0017':
        Dataset '/group_0000/subgroup_0001/dataset_0019':
        Dataset '/group_0000/subgroup_0001/dataset_0021':
    Channel '':
    Channel '':
Calibration Group 'group_0001':
```
# By summary_nhf_measurement method in nm_io.py
```
Measurement (<class 'nanosurf.lib.util.nhf_reader.NHFMeasurement'>):
Nanosurf Studio v13.9-5690dfa64f
# channel  ['coordinates_x', 'coordinates_y']
     coordinates_x (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): , shape: (2500,), unit: 
     coordinates_y (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): , shape: (2500,), unit: 
# segment: ['Advance to Setpoint 1', 'Retract 1']
     Advance to Setpoint 1 (<class 'nanosurf.lib.util.nhf_reader.NHFSegment'>):
        Channels: ['Topography', 'Z-Controller In', 'Deflection', 'Position Z', 'Position X', 'Position Y', 'X-Controller Out', 'Y-Controller Out', 'Sampler Meta Channel', 'Sampler Timestamp', 'Time']
             Topography (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Topography, shape: (2755000,), unit: m
             Z-Controller In (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Z-Controller In, shape: (2755000,), unit: V
             Deflection (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Deflection, shape: (2755000,), unit: V
             Position Z (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Position Z, shape: (2755000,), unit: m
             Position X (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Position X, shape: (2755000,), unit: m
             Position Y (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Position Y, shape: (2755000,), unit: m
             X-Controller Out (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): X-Controller Out, shape: (2755000,), unit: m
             Y-Controller Out (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Y-Controller Out, shape: (2755000,), unit: m
             Sampler Meta Channel (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Sampler Meta Channel, shape: (2755000,), unit: int
             Sampler Timestamp (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Sampler Timestamp, shape: (2755000,), unit: int
             Time (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Time, shape: (2755000,), unit: s
     Retract 1 (<class 'nanosurf.lib.util.nhf_reader.NHFSegment'>):
        Channels: ['Topography', 'Z-Controller In', 'Deflection', 'Position Z', 'Position X', 'Position Y', 'X-Controller Out', 'Y-Controller Out', 'Sampler Meta Channel', 'Sampler Timestamp', 'Time']
             Topography (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Topography, shape: (2755000,), unit: m
             Z-Controller In (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Z-Controller In, shape: (2755000,), unit: V
             Deflection (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Deflection, shape: (2755000,), unit: V
             Position Z (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Position Z, shape: (2755000,), unit: m
             Position X (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Position X, shape: (2755000,), unit: m
             Position Y (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Position Y, shape: (2755000,), unit: m
             X-Controller Out (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): X-Controller Out, shape: (2755000,), unit: m
             Y-Controller Out (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Y-Controller Out, shape: (2755000,), unit: m
             Sampler Meta Channel (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Sampler Meta Channel, shape: (2755000,), unit: int
             Sampler Timestamp (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Sampler Timestamp, shape: (2755000,), unit: int
             Time (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>):
                        Dataset: (<class 'nanosurf.lib.util.nhf_reader.NHFDataset'>): Time, shape: (2755000,), unit: s
```
