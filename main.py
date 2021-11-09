# -*- encoding: utf8 -*-
"""
ktlint 工具
功能: kotlin代码分析
用法: python3 main.py

本地调试步骤:
1. 添加环境变量: export SOURCE_DIR="xxx/src_dir"
2. 添加环境变量: export TASK_REQUEST="xxx/task_request.json"
3. 按需修改task_request.json文件中各字段的内容
4. 命令行cd到项目根目录,执行命令:  python3 src/main.py
"""

# 2021-02-22    kylinye    created

import os
import json
import subprocess
import sys
import xml.etree.ElementTree as ET


class Ktlint(object):
    def __get_task_params(self):
        """
        获取需要任务参数
        :return:
        """
        task_request_file = os.environ.get("TASK_REQUEST")
        with open(task_request_file, 'r') as rf:
            task_request = json.load(rf)
        task_params = task_request["task_params"]

        return task_params

    def __get_dir_files(self, root_dir, want_suffix=""):
        """
        在指定的目录下,递归获取符合后缀名要求的所有文件
        :param root_dir:
        :param want_suffix:
                    str|tuple,文件后缀名.单个直接传,比如 ".py";多个以元组形式,比如 (".h", ".c", ".cpp")
                    默认为空字符串,会匹配所有文件
        :return: list, 文件路径列表
        """
        files = set()
        for dirpath, _, filenames in os.walk(root_dir):
            for f in filenames:
                if f.lower().endswith(want_suffix):
                    fullpath = os.path.join(dirpath, f)
                    files.add(fullpath)
        files = list(files)
        return files

    def run(self):
        """
        :return:
        """
        # 代码目录直接从环境变量获取
        source_dir = os.environ.get("SOURCE_DIR", None)
        # source_dir = "/Users/kylinye/Documents/UGit/example/kotlin_example"
        print("[debug] source_dir: %s" % source_dir)

        # 其他参数从task_request.json文件获取
        task_params = self.__get_task_params()
        # 规则
        rules = task_params["rules"]

        # ------------------------------------------------------------------ #
        # 增量扫描时,可以通过环境变量获取到diff文件列表,只扫描diff文件,减少耗时
        # 此处获取到的diff文件列表,已经根据项目配置的过滤路径过滤
        # ------------------------------------------------------------------ #
        # 需要扫描的文件后缀名
        want_suffix = (".kt")
        # 从 DIFF_FILES 环境变量中获取增量文件列表存放的文件(全量扫描时没有这个环境变量)
        diff_file_json = os.environ.get("DIFF_FILES")
        if diff_file_json:  # 如果存在 DIFF_FILES, 说明是增量扫描, 直接获取增量文件列表
            print("get diff file: %s" % diff_file_json)
            with open(diff_file_json, "r") as rf:
                diff_files = json.load(rf)
                scan_files = [path for path in diff_files if path.lower().endswith(want_suffix)]
        else:  # 未获取到环境变量,即全量扫描,遍历source_dir获取需要扫描的文件列表
            scan_path = os.path.join(source_dir, "**/*.kt")
            scan_files = [scan_path]

        # todo: 此处实现工具逻辑,输出结果,存放到result字典中
        # 设置配置文件、输出文件和结果文件
        error_output = "error_output.xml"
        result_output = "result.json"
        if os.path.exists(result_output):
            os.remove(result_output)
        result=[]

        cmd = [
            "./ktlint",
            "--reporter=checkstyle,output=%s" % error_output
        ]

        if not scan_files:
            print("[error] To-be-scanned files is empty")
            with open(result_output, "w") as fp:
                json.dump(result, fp, indent=2)
            return
        cmd.extend(scan_files)

        scan_cmd = " ".join(cmd)
        print("[debug] cmd: %s" % scan_cmd)
        subproc = subprocess.Popen(scan_cmd,
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT,
                                   shell=True)
        subproc.wait()

         # 数据处理
        if os.path.exists(error_output):
            tree = ET.ElementTree(file=error_output)
            for elem in tree.iter():
                if elem.tag == "file":
                    file_path = elem.attrib['name']
                    if not file_path.endswith('.kt'):
                        continue
                    for sub_elem in elem.iter():        
                        if sub_elem.tag == "error":
                            issue = {}
                            issue['path'] = file_path
                            issue['line'] = sub_elem.attrib['line']
                            issue['column'] = sub_elem.attrib['column']
                            issue['msg'] = sub_elem.attrib['message']
                            if not sub_elem.attrib['source'] in rules:
                                continue
                            issue['rule'] = sub_elem.attrib['source']
                            if issue != {}:
                                result.append(issue)
        else:
            print("[error] cannot load ktlint outputs: %s" % error_output)

        # 输出结果到指定的json文件
        with open(result_output, "w") as fp:
            json.dump(result, fp, indent=2)

if __name__ == '__main__':
    print("-- start run tool ...")
    Ktlint().run()
    print("-- end ...")