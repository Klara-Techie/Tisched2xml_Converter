# Tisched2xml converter Tool
## Description
* This tool is designed to convert the Tisched to xml format. So it can be used in another tools which developed based xml format and some potential errors can be resolved

## Features
""" Info of v1.3.0 tool """
* Tisched to xml converter
* Prefix will be changed as per req
* Sections will be seperated 
* Commented Process, Events and Isr will not be scheduled 
* For Event space around the :: has been handled 
* For Empty task body warning will be logged 

#  In development 
* GUI update's 

#  Flow of the code 
1. Extract the data from the given .tisched file by using extract_task_info()
2. The extracted data need to be processed by using format_process_event()
3. The processed data need to be written in the xml file by using write_xml_from_dict()
4. Front-end: ui_tisched()
