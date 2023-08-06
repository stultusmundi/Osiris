from utils import run_command
from ast_walker import AstWalker, AstWalker_Sup_high
import json

class AstHelper:
    def __init__(self, filename, high_ver):
        self.source_list = self.get_source_list(filename)
        self.high_ver = high_ver
        self.contracts = self.extract_contract_definitions(self.source_list)

    def get_source_list(self, filename):
        cmd = "solc --combined-json ast %s" % filename
        out = run_command(cmd)
        out = json.loads(out)
        return out["sources"]

    def extract_contract_definitions(self, sourcesList):
        ret = {
            "contractsById": {},
            "contractsByName": {},
            "sourcesByContract": {}
        }
        if self.high_ver:
            walker = AstWalker_Sup_high()
        else:
            walker = AstWalker()
        for k in sourcesList:
            nodes = []
            if self.high_ver:
                walker.walk(sourcesList[k]["AST"], {"nodeType": "ContractDefinition"}, nodes)#    0.8
            else:
                walker.walk(sourcesList[k]["AST"], "ContractDefinition", nodes) #0.7
            
            for node in nodes:
                ret["contractsById"][node["id"]] = node
                ret["sourcesByContract"][node["id"]] = k
                if self.high_ver:
                    ret["contractsByName"][k + ':' + node["name"]] = node # 0.8
                else:
                    ret["contractsByName"][k + ':' + node["attributes"]["name"]] = node # 0.7
        return ret

    def get_linearized_base_contracts(self, id, contractsById):
        if self.high_ver:
            return map(lambda id: contractsById[id], contractsById[id]["linearizedBaseContracts"])  #0.8
        else:
            return map(lambda id: contractsById[id], contractsById[id]["attributes"]["linearizedBaseContracts"])    #0.7

    def extract_state_definitions(self, c_name):
        node = self.contracts["contractsByName"][c_name]
        state_vars = []
        if node:
            base_contracts = self.get_linearized_base_contracts(node["id"], self.contracts["contractsById"])
            base_contracts = list(reversed(list(base_contracts)))
            for contract in base_contracts:
                if "children" in contract:
                    for item in contract["children"]:
                        if item["name"] == "VariableDeclaration":
                            state_vars.append(item)
                if "nodes" in contract:
                    for item in contract["nodes"]:
                        if item["nodeType"] == "VariableDeclaration":
                            state_vars.append(item)
        return state_vars

    def extract_states_definitions(self):
        ret = {}
        for contract in self.contracts["contractsById"]:
            if self.high_ver:
                name = self.contracts["contractsById"][contract]["name"]#0.8
            else:
                name = self.contracts["contractsById"][contract]["attributes"]["name"]  #0.7
            source = self.contracts["sourcesByContract"][contract]
            full_name = source + ":" + name
            ret[full_name] = self.extract_state_definitions(full_name)
        return ret

    def extract_func_call_definitions(self, c_name):
        node = self.contracts["contractsByName"][c_name]
        if self.high_ver:
            walker = AstWalker_Sup_high()
        else:
            walker = AstWalker()
        nodes = []
        if node:
            walker.walk(node, "FunctionCall", nodes)
            if self.high_ver:
                walker.walk(node, {"nodeType":  "FunctionCall"}, nodes)
            else:
                walker.walk(node, "FunctionCall", nodes)
        return nodes

    def extract_func_calls_definitions(self):
        ret = {}
        for contract in self.contracts["contractsById"]:
            if self.high_ver:
                name = self.contracts["contractsById"][contract]["name"]#0.8
            else:
                name = self.contracts["contractsById"][contract]["attributes"]["name"]  #0.7
            source = self.contracts["sourcesByContract"][contract]
            full_name = source + ":" + name
            ret[full_name] = self.extract_func_call_definitions(full_name)
        return ret

    def extract_state_variable_names(self, c_name):
        state_variables = self.extract_states_definitions()[c_name]
        var_names = []
        for var_name in state_variables:
            if self.high_ver:
                var_names.append(var_name["name"])#0.8
            else:
                var_names.append(var_name["attributes"]["name"])  #0.7
        return var_names

    def extract_func_call_srcs(self, c_name):
        func_calls = self.extract_func_calls_definitions()[c_name]
        func_call_srcs = []
        for func_call in func_calls:
            func_call_srcs.append(func_call["src"])
        return func_call_srcs
