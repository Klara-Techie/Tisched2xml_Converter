""" Info of v1.3.0 tool """
# Tisched to xml converter
# RTE_Task_ will be added as prefix for events 
# Code sharing will be added in a separate section 
# TaskEndHook will be stored in a separate section 
# Commented Process, Events and Isr will not be scheduled 
# For Event space around the :: has beed handled 
# For Empty task body warning will be logged 

""" In development """
# GUI update's 

""" Flow of the code """
# 1. Extract the data from the given .tisched file by using extract_task_info()
# 2. The extracted data need to be processed by using format_process_event()
# 3. The processed data need to be written in the xml file by using write_xml_from_dict()
# 4. Front-end: ui_tisched()

import re
import os
import logging
import json
import xml.dom.minidom
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import threading
from tkinter import messagebox

tool_version = "v1.3.3" # Tool version can be updated over here
DEBUG_MODE = False  # Set this to True for debugging print statements

# 1. Extract the data from the given .tisched
# Working TaskEndHook

# Input: rba_osarschedextn_schedcfg.tisched
# Output: dict_of_task_body
'''
{
    'OS_2Q1_ReIni_Task': 
        {
            'bosch_processes_events': [('Process', 'DAVSE_Proc_ReIni', None, 6),('Process', 'app2sv_Proc_ReIni', None, 8)],
            'vw_processes_events': [('Process', 'ComVeh2_SwSVW_Proc_In_Eng_bSailPhdLs2Diag_VW_ReIni', None, 11)],
            'end_hook_processes_events': [('Process', 'rba_Distab_T20ms_Proc', None, 14)]
        }
}

process_event_pattern = r"(?<!\S)/\*.*?\*/|\b(Process|Event)\s+([^\s:]+)(?:\s*::\s*([^\s]+))?(?![^/\r\n]*\*/)"

(?<!\S)           # Ensure the start is not preceded by a non-whitespace character
/\*.*?\*/         # Match and consume a C-style block comment (/* ... */)
|                 # OR
\b                # Word boundary (ensure 'Process' or 'Event' is a whole word)
(Process|Event)   # Match 'Process' or 'Event'
\s+               # Match one or more whitespace characters
([^\s:]+)         # Capture one or more characters that are not whitespace or a colon
(?:               # Start non-capturing group (for '::' part)
  \s*::\s*        # Match '::' surrounded by optional whitespace
  ([^\s]+)        # Capture one or more non-whitespace characters
)?                # End non-capturing group, make it optional
(?!               # Negative lookahead to ensure the following is not:
  [^/\r\n]*       # Any characters except '/' or newline
  \*/             # End of a block comment (*/)
)


# '''

full_formatted_data = {}

def extract_task_info(file_path, task_or_isr_name, task_or_isr, file_directory):
    global full_formatted_data
    # Configure logging
    log_file = os.path.join(file_directory, 'tisched_error_log.txt')
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    
    def find_processes_events(body, start_line):
        processes_events = []
        if task_or_isr == "Task":                
            for match in re.finditer(process_event_pattern, body):
                line_number = start_line + body[:match.start()].count('\n') + 3
                processes_events.append((match.group(1), match.group(2), match.group(3), line_number))
        elif task_or_isr == "ISR":
            for match in re.finditer(process_event_pattern, body):
                line_number = start_line + body[:match.start()].count('\n') + 1
                processes_events.append((match.group(1), match.group(2), match.group(3), line_number))
        else:
            '''Do nothing'''
        return processes_events

    try:
        # Open and read the content from the given file
        with open(file_path, 'r') as file:
            content = file.read()
            if task_or_isr == "Task":
                # Define regex patterns to match task, process, and event
                task_pattern = r"Task\s+" + re.escape(task_or_isr_name) + r"\s*{\s*TaskBody\s*{([^}]*)}\s*(?:TaskEndHook\s*{([^}]*)})?\s*}"
                # process_event_pattern = r"(Process|Event)\s+([^\s:]+)(?:\s*::\s*([^\s]+))?(?![^/\r\n]*\*/)"
                # process_event_pattern = r"(?<!/\*)\b(Process|Event)\s+([^\s:]+)(?:\s*::\s*([^\s]+))?(?![^/\r\n]*\*/)"
                process_event_pattern = r"(?<!\S)/\*.*?\*/|\b(Process|Event)\s+([^\s:]+)(?:\s*::\s*([^\s]+))?(?![^/\r\n]*\*/)"

                # Extract task body for the given task name
                task_match = re.search(task_pattern, content, re.DOTALL)
                if task_match:
                    task_body = task_match.group(1)
                    task_end_hook_body = task_match.group(2) if task_match.group(2) else ""
                    # task_start_line = content[:task_match.start()].count('\n') + 1
                    # Calculate start line number accurately
                    task_start_index = task_match.start()
                    task_start_line = content[:task_start_index].count('\n') + 1

                    # Split the Bosch and VW process and event
                    codesharing_pattern = r'/\*Codesharing\s' + re.escape(task_or_isr_name.split('_')[-2]) + r'\ssection\*/'
                    split_task_body = re.split(codesharing_pattern, task_body)

                    bosch_task_body = split_task_body[0]
                    vw_task_body = split_task_body[1] if len(split_task_body) > 1 else ""

                    bosch_processes_events = []
                    vw_processes_events = []

                    bosch_processes_events.extend(find_processes_events(bosch_task_body, task_start_line))

                    vw_processes_events.extend(find_processes_events(vw_task_body, task_start_line + bosch_task_body.count('\n')))

                    end_hook_processes_events = []
                    if task_end_hook_body:
                        end_hook_processes_events.extend(find_processes_events(task_end_hook_body, task_start_line + bosch_task_body.count('\n') + vw_task_body.count('\n')))

                    dict_of_task_body = {
                        task_or_isr_name: {
                            "bosch_processes_events": bosch_processes_events,
                            "vw_processes_events": vw_processes_events,
                            "end_hook_processes_events": end_hook_processes_events
                        }
                    }
                    
                    final_dict = format_process_event(dict_of_task_body)
                    update_tasks(final_dict)
                    # print(full_formatted_data)
                    
                    if DEBUG_MODE:
                        print("dict_of_task_body = ")
                        pretty_dict_of_task_body = json.dumps(dict_of_task_body, indent=4, sort_keys=True)
                        print(pretty_dict_of_task_body, '\n')
                        print("Formatted_data = ")
                        pretty_final_dict = json.dumps(final_dict, indent=4, sort_keys=True)
                        print(pretty_final_dict)
                    else:
                        pass
                    
                    return final_dict

                else:
                    logging.error("TaskBody not found: %s", task_or_isr_name)
                    return "TaskBody not found"

            elif task_or_isr == "ISR":
                isr_pattern = r"Isr\s+" + re.escape(task_or_isr_name) + r"\s*{([^}]*)}"
                # process_event_pattern = r"(Process|IsrEntity)\s+([^\s:]+)(?:\s*::\s*([^\s]+))?(?![^/\r\n]*\*/)"
                process_event_pattern = r"(?<!\S)/\*.*?\*/|\b(Process|IsrEntity)\s+([^\s:]+)(?:\s*::\s*([^\s]+))?(?![^/\r\n]*\*/)"

                isr_match = re.search(isr_pattern, content, re.DOTALL)
                if isr_match:
                    isr_body = isr_match.group(1)
                    
                    codesharing_pattern = r'/\*Codesharing\s' + re.escape(task_or_isr_name.split('_')[-2]) + r'\ssection\*/'
                    split_isr_body = re.split(codesharing_pattern, isr_body)
                    
                    bosch_isr_body = split_isr_body[0]
                    vw_isr_body = split_isr_body[1] if len(split_isr_body) > 1 else ""

                    bosch_processes_events = []
                    vw_processes_events = []
                    end_hook_processes_events = []
                    
                    bosch_processes_events = find_processes_events(bosch_isr_body, content[:isr_match.start()].count('\n') + 1)
                    vw_processes_events = find_processes_events(vw_isr_body, content[:isr_match.start()].count('\n') + 1)
                    
                    dict_of_task_body = {
                        task_or_isr_name: {
                            "bosch_processes_events": bosch_processes_events,
                            "vw_processes_events": vw_processes_events,
                            "end_hook_processes_events": end_hook_processes_events
                        }
                    }
                    
                    final_dict = format_process_event(dict_of_task_body)
                    update_tasks(final_dict)
                    # print(full_formatted_data)
                    
                    if DEBUG_MODE:
                        pretty_dict_of_task_body = json.dumps(dict_of_task_body, indent=4, sort_keys=True)
                        print("dict_of_task_body = ", pretty_dict_of_task_body, '\n')

                        pretty_final_dict = json.dumps(final_dict, indent=4, sort_keys=True)
                        print("Formatted_data = ", pretty_final_dict, '\n')
                    else:
                        pass
                    
                    return final_dict  
                
                else:
                    logging.error("Isr not found: %s", task_or_isr_name)
                    return "Isr not found"

    except FileNotFoundError:
        logging.error("File not found: %s", file_path)
        return "File not found"
    except IndexError:
        logging.error("IndexError occurred while processing task body: %s", task_or_isr_name)
        return "Error occurred while processing task body"
    except Exception as e:
        logging.error("An unexpected error occurred: %s", str(e))
        return "An unexpected error occurred"
# End of extract_task_info()-------------------------------------------------------------------------------------------------------------------------------------

# 2. The extracted data need to be processed by using format_process_event()
# Input: dict_of_task_body from extract_task_info()
# Output: formatted_data
'''
{
    'OS_ReIni_Task': 
    {
        'f_bosch_processes_events': ['DAVSE_Proc_ReIni', 'RTE_Task_ETO_MoExe_Co_Proc_ReIni_2Q1_10ms_OsApp_2_Q_1_Task10ms_Nr1', 'app2sv_Proc_ReIni'], 
        'f_vw_processes_events': ['ComVeh2_SwSVW_Proc_In_Eng_bSailPhdLs2Diag_VW_ReIni'], 
        'f_end_hook_proc_eve': ['rba_Distab_T20ms_Proc']
    }
}
'''
def update_tasks(tasks):
    """
    Updates the tasks dictionary by adding process and events to the appropriate categories (Codesharing and TaskEndHook).
    
    Parameters:
    tasks (dict): The dictionary containing tasks and their associated process and events.
    """

    global full_formatted_data
    for task_name, categories in tasks.items():
        if task_name not in full_formatted_data:
            full_formatted_data[task_name] = {}
        
        for category_name, process_events in categories.items():
            if process_events:  # Check if the list of process_events is not empty
                if category_name not in full_formatted_data[task_name]:
                    full_formatted_data[task_name][category_name] = []
                for event in process_events:
                    full_formatted_data[task_name][category_name].append(event)


def format_process_event(dict_of_body):
    formatted_rb_proc_eve = []
    formatted_vw_proc_eve = []
    formatted_end_hook_proc_eve = []
    f_task_or_isr_name = ""
    pattern = r"OS_\d+[A-Za-z]+\d+"
    
    for task_or_isr_name, task_or_isr_data in dict_of_body.items():
        f_task_or_isr_name = re.sub(pattern, "OS", task_or_isr_name)
    
        for bosch_process_or_events in task_or_isr_data['bosch_processes_events']:
            if len(bosch_process_or_events) == 3:
                bosch_process_or_events = bosch_process_or_events + (None,)
            line_number = bosch_process_or_events[3]
            if bosch_process_or_events[0] == 'Process' and bosch_process_or_events[1] is not None and len(bosch_process_or_events[1]) > 0:
                formatted_rb_proc_eve.append(bosch_process_or_events[1])
            elif bosch_process_or_events[0] == 'Event' and bosch_process_or_events[2] is not None and len(bosch_process_or_events[2]) > 0:
                temp_rb_eve = "RTE_Task_{}".format(bosch_process_or_events[2])
                formatted_rb_proc_eve.append(temp_rb_eve)
            elif bosch_process_or_events[0] == 'IsrEntity' and bosch_process_or_events[2] is not None and len(bosch_process_or_events[2]) > 0:
                temp_rb_entity = "RTE_Task_{}".format(bosch_process_or_events[2])
                formatted_rb_proc_eve.append(temp_rb_entity)
            else:
                if bosch_process_or_events[0] == None and bosch_process_or_events[1] == None and bosch_process_or_events[2] == None:
                    ''' Do nothing '''
                else:
                    logging.error("Invalid input detected for %s in bosch_processes_events at line %s: %s", 
                                task_or_isr_name, line_number, bosch_process_or_events)
                
        for vw_process_or_events in task_or_isr_data['vw_processes_events']:
            if len(vw_process_or_events) == 3:
                vw_process_or_events = vw_process_or_events + (None,)
            line_number = vw_process_or_events[3]
            if vw_process_or_events[0] == 'Process' and vw_process_or_events[1] is not None and len(vw_process_or_events[1]) > 0:
                formatted_vw_proc_eve.append(vw_process_or_events[1])
            elif vw_process_or_events[0] == 'Event' and vw_process_or_events[2] is not None and len(vw_process_or_events[2]) > 0:
                temp_vw_eve = "RTE_Task_{}".format(vw_process_or_events[2])
                formatted_vw_proc_eve.append(temp_vw_eve)
            elif vw_process_or_events[0] == 'IsrEntity' and vw_process_or_events[2] is not None and len(vw_process_or_events[2]) > 0:
                temp_rb_entity = "RTE_Task_{}".format(vw_process_or_events[2])
                formatted_vw_proc_eve.append(temp_rb_entity)
            else:
                if vw_process_or_events[0] == None and vw_process_or_events[1] == None and vw_process_or_events[2] == None:
                    ''' Do nothing '''
                else:
                    logging.error("Invalid input detected for %s in bosch_processes_events at line %s: %s", 
                                task_or_isr_name, line_number, vw_process_or_events)
                
        for end_hook_processes_events in task_or_isr_data['end_hook_processes_events']:
            if len(end_hook_processes_events) == 3:
                end_hook_processes_events = end_hook_processes_events + (None,)
            line_number = end_hook_processes_events[3]
            if end_hook_processes_events[0] == 'Process' and end_hook_processes_events[1] is not None:
                formatted_end_hook_proc_eve.append(end_hook_processes_events[1])
            elif end_hook_processes_events[0] == 'Event' and end_hook_processes_events[2] is not None:
                temp_rb_eve = "RTE_Task_{}".format(end_hook_processes_events[2])
                formatted_end_hook_proc_eve.append(temp_rb_eve)
            elif end_hook_processes_events[0] == 'IsrEntity' and end_hook_processes_events[2] is not None:
                temp_rb_entity = "RTE_Task_{}".format(end_hook_processes_events[2])
                formatted_end_hook_proc_eve.append(temp_rb_entity)
            else:
                if end_hook_processes_events[0] == None and end_hook_processes_events[1] == None and end_hook_processes_events[2] == None:
                    ''' Do nothing '''
                else:
                    logging.error("Invalid input detected for %s in bosch_processes_events at line %s: %s", 
                                task_or_isr_name, line_number, end_hook_processes_events)   
                
    # Warning for empty Taskbody  
    if len(formatted_rb_proc_eve) == 0 and len(formatted_vw_proc_eve) == 0 and len(formatted_end_hook_proc_eve) == 0:
        logging.warning("Taskbody is empty: %s", task_or_isr_name)
    else:
        '''Proceed further'''
    formatted_data = {
        f_task_or_isr_name: {
            "f_bosch_processes_events": formatted_rb_proc_eve,
            "f_vw_processes_events": formatted_vw_proc_eve,
            "f_end_hook_proc_eve" : formatted_end_hook_proc_eve
        }
    }

    return formatted_data
# # End of format_process_event()-------------------------------------------------------------------------------------------------------------------------------------

# 3. The processed data need to be written in the xml file by using write_xml_from_dict()

def write_xml_from_dict(data_dict, xml_file_path):
    try:
        # Check if the XML file already exists
        if os.path.exists(xml_file_path):
            # Parse existing XML file
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            sw_tasks = root.find(".//SW-TASKS")
        else:
            # Create new XML root element
            root = ET.Element("MSRSW")
            tree = ET.ElementTree(root)

            # Add required XML elements with hardcoded values
            category = ET.SubElement(root, "CATEGORY")
            category.text = "Dy-Sched"

            # Add ADMIN-DATA section
            admin_data = ET.SubElement(root, "ADMIN-DATA")
            language = ET.SubElement(admin_data, "LANGUAGE")
            language.text = "en"
            company_doc_infos = ET.SubElement(admin_data, "COMPANY-DOC-INFOS")
            company_doc_info = ET.SubElement(company_doc_infos, "COMPANY-DOC-INFO")
            company_ref = ET.SubElement(company_doc_info, "COMPANY-REF")
            company_ref.text = "RB"
            sdgs = ET.SubElement(company_doc_info, "SDGS")
            sdg = ET.SubElement(sdgs, "SDG", {"GID": "RBHead-Nestor-Keywords"})
            for gid in ["Filename", "Author", "Function", "Domain", "User", "Date", "Class", "Name", "Variant", "Revision", "Type", "State", "FDEF", "History"]:
                ET.SubElement(sdg, "SD", {"GID": gid})

            # Add SW-SYSTEMS section
            sw_systems = ET.SubElement(root, "SW-SYSTEMS")
            sw_system = ET.SubElement(sw_systems, "SW-SYSTEM")
            long_name = ET.SubElement(sw_system, "LONG-NAME")
            long_name.text = "MDG1"
            short_name = ET.SubElement(sw_system, "SHORT-NAME")
            short_name.text = "MG1"
            sw_scheduling_spec = ET.SubElement(sw_system, "SW-SCHEDULING-SPEC")
            sw_task_spec = ET.SubElement(sw_scheduling_spec, "SW-TASK-SPEC")
            sw_tasks = ET.SubElement(sw_task_spec, "SW-TASKS")

            # Add SW-COMPONENT-SPEC after SW-SCHEDULING-SPEC
            sw_component_spec = ET.SubElement(sw_system, "SW-COMPONENT-SPEC")
            sw_components = ET.SubElement(sw_component_spec, "SW-COMPONENTS")
            sw_feature = ET.SubElement(sw_components, "SW-FEATURE")
            short_name = ET.SubElement(sw_feature, "SHORT-NAME")
            short_name.text = "OS"
            category = ET.SubElement(sw_feature, "CATEGORY")
            category.text = "PRJ"

            # Add MATCHING-DCIS after SW-SYSTEMS
            matching_dcis = ET.SubElement(root, "MATCHING-DCIS")
            matching_dci = ET.SubElement(matching_dcis, "MATCHING-DCI")
            short_label = ET.SubElement(matching_dci, "SHORT-LABEL")
            short_label.text = "Dy-Sched"

        # Add SW-TASK elements based on the input dictionary
        for task_name, task_data in data_dict.items():
            sw_task = ET.SubElement(sw_tasks, "SW-TASK")
            short_name = ET.SubElement(sw_task, "SHORT-NAME")
            short_name.text = task_name
            sw_process_lists = ET.SubElement(sw_task, "SW-PROCESS-LISTS")

            # Add Bosch processes as SW-SERVICE-REFS
            if "f_bosch_processes_events" in task_data:
                # if len(task_data["f_bosch_processes_events"]) > 0:
                    sw_process_list = ET.SubElement(sw_process_lists, "SW-PROCESS-LIST")
                    short_label = ET.SubElement(sw_process_list, "SHORT-LABEL")
                    # short_label.text = f"{task_name.split('_')[-2]} Process Section"  
                    short_label.text = " "
                    sw_service_refs = ET.SubElement(sw_process_list, "SW-SERVICE-REFS")
                    if len(task_data["f_bosch_processes_events"]) > 0:
                        for bosch_processes_events in task_data["f_bosch_processes_events"]:
                            sw_service_ref = ET.SubElement(sw_service_refs, "SW-SERVICE-REF")
                            sw_service_ref.text = bosch_processes_events
                    else:
                        sw_service_ref = ET.SubElement(sw_service_refs, "SW-SERVICE-REF")
                        sw_service_ref.text = " "


            # Add VW processes as SW-SERVICE-REFS
            if "f_vw_processes_events" in task_data:
                if len(task_data["f_vw_processes_events"]) > 0:
                    sw_process_list = ET.SubElement(sw_process_lists, "SW-PROCESS-LIST")
                    short_label = ET.SubElement(sw_process_list, "SHORT-LABEL")
                    short_label.text = "Codesharing section"
                    # short_label.text = f"{task_name.split('_')[-2]} VW Process Section"
                    sw_service_refs = ET.SubElement(sw_process_list, "SW-SERVICE-REFS")
                    for vw_processes_events in task_data["f_vw_processes_events"]:
                        sw_service_ref = ET.SubElement(sw_service_refs, "SW-SERVICE-REF")
                        sw_service_ref.text = vw_processes_events

            # Add Bosch End Hook processes as SW-SERVICE-REFS
            if "f_end_hook_proc_eve" in task_data:
                if len(task_data["f_end_hook_proc_eve"]) > 0:
                    sw_process_list = ET.SubElement(sw_process_lists, "SW-PROCESS-LIST")
                    short_label = ET.SubElement(sw_process_list, "SHORT-LABEL")
                    short_label.text = "TaskEndHook"
                    sw_service_refs = ET.SubElement(sw_process_list, "SW-SERVICE-REFS")
                    for bosch_end_hook_processes_events in task_data["f_end_hook_proc_eve"]:
                        sw_service_ref = ET.SubElement(sw_service_refs, "SW-SERVICE-REF")
                        sw_service_ref.text = bosch_end_hook_processes_events

        # Write XML content to file
        tree.write(xml_file_path, encoding="ISO-8859-1")

        # print("Data appended successfully.")
    except Exception as e:
        logging.error("An unexpected error occurred while writing XML: %s", str(e))
        print("Error:", str(e))
# End of write_xml_from_dict()-------------------------------------------------------------------------------------------------------------------------------------

def pretty_print_xml(xml_file_path):
    # Parse the XML file
    dom = xml.dom.minidom.parse(xml_file_path)

    # Pretty print the XML content
    pretty_xml = dom.toprettyxml(encoding="ISO-8859-1")

    # Write the pretty printed XML back to the file
    with open(xml_file_path, "wb") as file:
        file.write(pretty_xml)
    
# To reset the global full_formatted_data

def reset_full_formatted_data():
    global full_formatted_data
    full_formatted_data = {}
    
        
# 4. Fron-end: ui_tisched()-------------------------------------------------------------------------------------------------------------------------------------

#Tested Okay with ui and error handling 
def ui_tisched():
    global full_formatted_data
    def process_file():
        global full_formatted_data
        try:
            # Check if the file path is provided
            tisched_file = file_entry.get()
            file_directory = os.path.dirname(tisched_file)
            out_file = os.path.join(file_directory, 'rba_osshell_sched_dy.xml')

            # Check if the file is empty
            if os.path.getsize(tisched_file) == 0:
                messagebox.showwarning("Empty File", "The selected file is empty. Please select a valid file.")
                progress_status_label.config(text="The selected file is empty. Please select a valid file.")
                return

            if os.path.exists(out_file):
                # If the output file already exists, ask for confirmation to overwrite
                confirm_overwrite = messagebox.askyesno("File Already Exists", "The rba_osshell_sched_dy.xml file already exists. Do you want to overwrite it?")
                if not confirm_overwrite:
                    return  # Do not proceed further if user chooses not to overwrite

                # If user confirms overwrite, delete the existing file
                os.remove(out_file)

            if tisched_file:
                # Disable the start button to prevent multiple clicks
                process_button.config(state="disabled")

                # Define the processing function
                def process():
                    global full_formatted_data
                    total_task_isr = 0
                    processed_task_isr = 0
                    with open(tisched_file, 'r') as file:
                        # Read lines from the file
                        lines = file.readlines()
                        total_task_isr_list = []
                        for line in lines:
                            # Check if the line starts with "Task "
                            if line.startswith("Task "):
                                # Extract the task name
                                task_name = line.strip()[5:]  # Removes "Task " from the beginning of the line                
                                total_task_isr_list.append(task_name)
                            elif line.startswith("Isr "):
                                isr_name = line.strip()[4:]  # Removes "Task " from the beginning of the line                   
                                total_task_isr_list.append(isr_name)

                        total_task_isr = len(total_task_isr_list)

                        # Iterate over each line
                        for line in lines:
                            # Check if the line starts with "Task "
                            if line.startswith("Task "):
                                # Extract the task name
                                task_name = line.strip()[5:]  # Removes "Task " from the beginning of the line                
                                task_or_isr = f"Task"
                                print("Task : ", task_name)
                                task_info = extract_task_info(tisched_file, task_name, task_or_isr, file_directory)
                                if task_info == "TaskBody not found":
                                    logging.error("%s - will not be written in the XML", task_name)
                                processed_task_isr = processed_task_isr + 1
                                progress = (processed_task_isr / total_task_isr) * 100
                                progress_bar["value"] = progress
                                progress_status_label.config(text=f"Processing {task_name}...")
                                progress_percentage_label.config(text=f"{progress:.2f}%")
                                root.update_idletasks()
                            elif line.startswith("Isr "):
                                isr_name = line.strip()[4:]  # Removes "Isr " from the beginning of the line                   
                                print("Isr : ", isr_name)
                                task_or_isr = f"ISR"
                                isr_info = extract_task_info(tisched_file, isr_name, task_or_isr, file_directory)
                                if isr_info == "Isr not found":
                                    logging.error("%s - will not be written in the XML", isr_name)
                                processed_task_isr = processed_task_isr + 1

                                progress = (processed_task_isr / total_task_isr) * 100
                                progress_bar["value"] = progress
                                progress_status_label.config(text=f"Processing {isr_name}...")
                                progress_percentage_label.config(text=f"{progress:.2f}%")
                                root.update_idletasks()
                        
                    write_xml_from_dict(full_formatted_data, out_file)
                    
                    if DEBUG_MODE: # Will print the whole content in the console and in log as a dict format 
                        pretty_full_formatted_data = json.dumps(full_formatted_data, indent=4, sort_keys=True)
                        print("pretty_full_formatted_data = ", pretty_full_formatted_data, '\n')
                        
                        logging.info("pretty_full_formatted_data =  %s ", 
                                pretty_full_formatted_data)
                    else:
                        pass

                    pretty_print_xml(out_file)   

                    progress_status_label.config(text=f"Completed...!")
                    print("done")

                    # Show completion notification
                    messagebox.showinfo("Process Completed", "completed!")

                    # Enable the start button
                    process_button.config(state="normal")

                    logging.info("Tool was executed successfully...!")
                    logging.info("XML file has been generated: %s", out_file)
                    logging.shutdown()

                    # Destroy the window
                    # root.destroy()

                # Start processing in a separate thread
                processing_thread = threading.Thread(target=process)
                processing_thread.start()
            else:
                messagebox.showwarning("No File Selected", "Please select a file.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")


    def browse_file():
        # Clear the file entry field
        file_entry.delete(0, tk.END)

        # Reset the progress status
        progress = 0
        progress_bar["value"] = progress
        progress_percentage_label.config(text=f"{progress:.2f}%")
        progress_status_label.config(text="")
        
        # Reset the global dictionary 
        reset_full_formatted_data()

        # Open file dialog to choose file
        file_path = filedialog.askopenfilename(title="Select .tisched file", filetypes=[("tisched files", "*.tisched")])

        if file_path:
            # Insert chosen file path into entry field
            file_entry.insert(tk.END, file_path)
            # Update the progress status label to show file loaded
            progress_status_label.config(text="File is loaded. Press start to continue.")
        else:
            # Update the progress status label to show error message
            progress_status_label.config(text="File path is empty, Load the .tisched file")

    def cancel():
        root.quit()
        root.destroy()
        
    # Create main window
    root = tk.Tk()
    root.title("Tisched2xml Converter {}".format(tool_version))

    # Label for file path
    file_label = tk.Label(root, text="tisched File:")
    file_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

    # Entry to display file path
    file_entry = tk.Entry(root, width=40)
    file_entry.grid(row=0, column=1, padx=10, pady=(10, 5))

    # Button to browse for file
    browse_button = tk.Button(root, text="Browse", command=browse_file)
    browse_button.grid(row=0, column=2, padx=10, pady=(10, 5))

    
#--------------------- Positioning for status, progress bar, percentage label --------------------------------------
    # Progress label
    progress_label = tk.Label(root, text="Status:")
    progress_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")  # Adjusted sticky to "e" for right alignment

    # Progress bar
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=150, mode="determinate", maximum=100)
    progress_bar.place(x=140, y=47)

    # Progress status label
    progress_percentage_label = tk.Label(root, text="")
    progress_percentage_label.place(x=290, y=47)
    
#----------------------------------------------------------------------------------------------------------------------
    
    # Progress status label
    progress_status_label = tk.Label(root, text="")
    progress_status_label.grid(row=2, column=0, columnspan=3, padx=10, pady=5)

    # Button frame
    button_frame = tk.Frame(root)
    button_frame.grid(row=3, column=0, columnspan=3, pady=(10, 5))

    # Button to start processing
    process_button = tk.Button(button_frame, text="Start", command=process_file)
    process_button.pack(side="left", padx=(10, 5))

    # Button to cancel
    cancel_button = tk.Button(button_frame, text="Cancel", command=cancel)
    cancel_button.pack(side="left", padx=(5, 10))

    # Run the application
    root.mainloop()
# End of ui_tisched()-------------------------------------------------------------------------------------------------------------------------------------

# 5. Call the ui 
ui_tisched()