#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算机模型机模拟器
5级流水线架构 | 统一编址 | 完整指令集
计算机组成原理课程设计
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from typing import List, Dict, Tuple, Optional
import os


class ALUFlags:
    """ALU标志位"""

    def __init__(self):
        self.V = 0  # 有符号数溢出
        self.C = 0  # 无符号数溢出/进位
        self.N = 0  # 负数标志
        self.Z = 0  # 零标志

    def update(self, result: int, width: int = 8):
        """更新标志位"""
        mask = (1 << width) - 1
        sign_bit = 1 << (width - 1)
        self.Z = 1 if (result & mask) == 0 else 0
        self.N = 1 if (result & sign_bit) != 0 else 0

    def update_add(self, a: int, b: int, result: int, width: int = 8):
        """加法标志位更新"""
        mask = (1 << width) - 1
        sign_bit = 1 << (width - 1)
        self.update(result, width)
        self.C = 1 if (a + b) > mask else 0
        a_sign = (a & sign_bit) != 0
        b_sign = (b & sign_bit) != 0
        r_sign = (result & sign_bit) != 0
        self.V = 1 if (a_sign == b_sign and a_sign != r_sign) else 0

    def update_sub(self, a: int, b: int, result: int, width: int = 8):
        """减法标志位更新"""
        mask = (1 << width) - 1
        sign_bit = 1 << (width - 1)
        self.update(result, width)
        self.C = 1 if a < b else 0
        a_sign = (a & sign_bit) != 0
        b_sign = (b & sign_bit) != 0
        r_sign = (result & sign_bit) != 0
        self.V = 1 if (a_sign != b_sign and a_sign != r_sign) else 0

    def to_byte(self) -> int:
        """转换为字节"""
        return (self.V << 3) | (self.C << 2) | (self.N << 1) | self.Z

    def from_byte(self, value: int):
        """从字节恢复"""
        self.V = (value >> 3) & 1
        self.C = (value >> 2) & 1
        self.N = (value >> 1) & 1
        self.Z = value & 1

    def __str__(self):
        return f"V={self.V} C={self.C} N={self.N} Z={self.Z}"


class PipelineStage:
    """流水线阶段定义"""
    IF = 0  # 取指
    ID = 1  # 译码
    OR = 2  # 取源操作数
    DR = 3  # 取目的操作数
    EX = 4  # 执行

    STAGE_NAMES = ["取指(IF)", "译码(ID)", "取源操作数(OR)", "取目的操作数(DR)", "执行(EX)"]


class Instruction:
    """指令类"""

    def __init__(self, opcode: int, machine_code: int):
        self.opcode = opcode
        self.machine_code = machine_code
        self.dest_reg = None
        self.src_reg = None
        self.immediate = None
        self.addr_mode = None
        self.mnemonic = ""

    def decode(self):
        """解码指令"""
        op = (self.machine_code >> 12) & 0xF
        op_names = {0x1: "ADD", 0x2: "SUB", 0x3: "MUL", 0x4: "INC", 0x5: "DEC",
                    0x7: "JMP", 0x8: "JC", 0xA: "MOV", 0xE: "LDI", 0x9: "LD", 0xF: "ST", 0x0: "NOP"}
        self.mnemonic = op_names.get(op, "???")

        if op == 0x1:  # ADD
            self.dest_reg = (self.machine_code >> 6) & 0x7
            self.src_reg = self.machine_code & 0x7
        elif op == 0x2:  # SUB
            self.dest_reg = (self.machine_code >> 6) & 0x7
            self.src_reg = self.machine_code & 0x7
        elif op == 0x3:  # MUL
            self.dest_reg = (self.machine_code >> 6) & 0x7
            self.src_reg = self.machine_code & 0x7
        elif op == 0x4:  # INC
            self.dest_reg = (self.machine_code >> 6) & 0x7
        elif op == 0x5:  # DEC
            self.dest_reg = (self.machine_code >> 6) & 0x7
        elif op == 0x7:  # JMP
            self.dest_reg = self.machine_code & 0x7
        elif op == 0x8:  # JC
            self.dest_reg = (self.machine_code >> 6) & 0x7
            cond = self.machine_code & 0x3
            cond_names = ["N", "Z", "C", "V"]
            self.mnemonic += cond_names[cond]
        elif op == 0xA:  # MOV
            self.dest_reg = (self.machine_code >> 6) & 0x7
            self.src_reg = self.machine_code & 0x7
        elif op == 0xE:  # LDI
            self.dest_reg = self.machine_code & 0x7
            self.immediate = (self.machine_code >> 4) & 0xFF
        elif op == 0x9:  # LD
            self.dest_reg = self.machine_code & 0x7
            self.immediate = (self.machine_code >> 4) & 0xFF
        elif op == 0xF:  # ST
            self.src_reg = self.machine_code & 0x7

    def __str__(self):
        if self.opcode == 0x1:
            return f"ADD r{self.dest_reg}, r{self.src_reg}"
        elif self.opcode == 0x2:
            return f"SUB r{self.dest_reg}, r{self.src_reg}"
        elif self.opcode == 0x3:
            return f"MUL r{self.dest_reg}, r{self.src_reg}"
        elif self.opcode == 0x4:
            return f"INC r{self.dest_reg}"
        elif self.opcode == 0x5:
            return f"DEC r{self.dest_reg}"
        elif self.opcode == 0x7:
            return f"JMP r{self.dest_reg}"
        elif self.opcode == 0x8:
            return f"JC r{self.dest_reg}"
        elif self.opcode == 0xA:
            return f"MOV r{self.dest_reg}, r{self.src_reg}"
        elif self.opcode == 0xE:
            return f"LDI r{self.dest_reg}, #{self.immediate}"
        elif self.opcode == 0x9:
            return f"LD r{self.dest_reg}, [{self.immediate}]"
        elif self.opcode == 0xF:
            return f"ST [R7], r{self.src_reg}"
        else:
            return "NOP"


class ModelMachine:
    """模型机核心类"""

    def __init__(self):
        # 存储器
        self.instruction_memory = [0] * 65536  # 指令存储器 16位宽
        self.data_memory = [0] * 65536  # 数据存储器 8位宽

        # 寄存器 (统一编址: r0-r7, SR)
        self.registers = [0] * 9
        self.pc = 0
        self.flags = ALUFlags()

        # 流水线寄存器
        self.pipeline_regs = {
            PipelineStage.IF: {'instruction': None, 'pc': 0},
            PipelineStage.ID: {'instruction': None, 'decoded_inst': None, 'pc': 0},
            PipelineStage.OR: {'instruction': None, 'src_val': None, 'dest_addr': None, 'pc': 0},
            PipelineStage.DR: {'instruction': None, 'src_val': None, 'dest_val': None, 'dest_addr': None, 'pc': 0},
            PipelineStage.EX: {'instruction': None, 'result': None, 'dest_addr': None, 'pc': 0}
        }

        # 状态
        self.cycle_log = []
        self.halted = False
        self.cycle_count = 0

        self._init_registers()

    def _init_registers(self):
        """初始化寄存器"""
        for i in range(9):
            self.registers[i] = 0
        self.pc = 0
        self.registers[8] = 0

    def reset(self):
        """系统复位"""
        self._init_registers()
        for i in range(5):
            self.pipeline_regs[i] = {'instruction': None, 'pc': 0}
            if i == PipelineStage.ID:
                self.pipeline_regs[i]['decoded_inst'] = None
            elif i == PipelineStage.OR:
                self.pipeline_regs[i]['src_val'] = None
                self.pipeline_regs[i]['dest_addr'] = None
            elif i == PipelineStage.DR:
                self.pipeline_regs[i]['src_val'] = None
                self.pipeline_regs[i]['dest_val'] = None
                self.pipeline_regs[i]['dest_addr'] = None
            elif i == PipelineStage.EX:
                self.pipeline_regs[i]['result'] = None
                self.pipeline_regs[i]['dest_addr'] = None

        self.halted = False
        self.cycle_count = 0
        self.cycle_log = []

    def load_program(self, filename: str) -> bool:
        """加载汇编程序"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                assembly_code = f.readlines()

            addr = 0
            labels = {}

            # 第一遍：收集标签
            for line in assembly_code:
                line = self._clean_line(line)
                if not line:
                    continue
                if ':' in line and not line.startswith(';'):
                    label = line.split(':')[0].strip()
                    labels[label] = addr
                    line = line.split(':', 1)[1].strip()
                    if not line:
                        continue
                if line:
                    addr += 2

            # 第二遍：汇编
            addr = 0
            for line in assembly_code:
                line = self._clean_line(line)
                if not line:
                    continue
                if ':' in line and not line.startswith(';'):
                    line = line.split(':', 1)[1].strip()
                    if not line:
                        continue

                machine_code = self._assemble_instruction(line, labels)
                if machine_code is not None:
                    self.instruction_memory[addr] = machine_code
                    addr += 2

            return True
        except Exception as e:
            print(f"加载程序错误: {e}")
            return False

    def _clean_line(self, line: str) -> str:
        """清理行内容"""
        line = line.strip()
        if not line or line.startswith(';'):
            return ""
        if ';' in line:
            line = line[:line.index(';')]
        return line.strip()

    def _assemble_instruction(self, line: str, labels: Dict) -> Optional[int]:
        """汇编单条指令"""
        parts = line.replace(',', ' ').split()
        if not parts:
            return None

        op = parts[0].lower()

        try:
            if op == 'add':
                _, rd, rs = parts
                rd_num = int(rd[1:])
                rs_num = int(rs[1:])
                return 0x1000 | (rd_num << 6) | rs_num
            elif op == 'sub':
                _, rd, rs = parts
                rd_num = int(rd[1:])
                rs_num = int(rs[1:])
                return 0x2000 | (rd_num << 6) | rs_num
            elif op == 'mul':
                _, rd, rs = parts
                rd_num = int(rd[1:])
                rs_num = int(rs[1:])
                return 0x3000 | (rd_num << 6) | rs_num
            elif op == 'inc':
                _, rd = parts
                rd_num = int(rd[1:])
                return 0x4000 | (rd_num << 6)
            elif op == 'dec':
                _, rd = parts
                rd_num = int(rd[1:])
                return 0x5000 | (rd_num << 6)
            elif op == 'jmp':
                if parts[1].startswith('r'):
                    rd_num = int(parts[1][1:])
                else:
                    rd_num = labels.get(parts[1], 0)
                return 0x7000 | rd_num
            elif op == 'jc':
                _, rd = parts
                rd_num = int(rd[1:])
                return 0x8000 | (rd_num << 6)
            elif op == 'mov':
                _, rd, rs = parts
                rd_num = int(rd[1:])
                rs_num = int(rs[1:])
                return 0xA000 | (rd_num << 6) | rs_num
            elif op == 'ldi':
                _, rd, imm = parts
                rd_num = int(rd[1:])
                imm_val = int(imm)
                return 0xE000 | (imm_val << 4) | rd_num
            elif op == 'ld':
                _, rd, addr = parts
                rd_num = int(rd[1:])
                addr_val = int(addr.strip('[]'))
                return 0x9000 | (addr_val << 4) | rd_num
            elif op == 'st':
                _, addr, rs = parts
                rs_num = int(rs[1:])
                return 0xF000 | rs_num
            elif op == 'nop':
                return 0x0000
        except Exception as e:
            print(f"汇编错误: {line}, {e}")
            return None
        return None

    def read_register(self, reg_addr: int) -> int:
        """读寄存器（支持统一编址）"""
        if 0 <= reg_addr <= 7:
            return self.registers[reg_addr]
        elif reg_addr == 8:
            return self.flags.to_byte()
        elif 0 <= reg_addr <= 65535:
            return self.data_memory[reg_addr]
        return 0

    def write_register(self, reg_addr: int, value: int):
        """写寄存器（支持统一编址）"""
        value &= 0xFF
        if 0 <= reg_addr <= 7:
            self.registers[reg_addr] = value
        elif reg_addr == 8:
            self.flags.from_byte(value)
        elif 0 <= reg_addr <= 65535:
            self.data_memory[reg_addr] = value

    def fetch(self) -> Optional[int]:
        """取指阶段"""
        if self.pc >= len(self.instruction_memory) or self.halted:
            return None
        instruction = self.instruction_memory[self.pc]
        self.pc += 2
        return instruction

    def decode(self, instruction: int) -> Instruction:
        """译码阶段"""
        inst = Instruction((instruction >> 12) & 0xF, instruction)
        inst.decode()
        return inst

    def read_operand(self, inst: Instruction, is_src: bool = True) -> int:
        """读取操作数"""
        if is_src:
            reg = inst.src_reg
        else:
            reg = inst.dest_reg

        if reg is not None:
            return self.read_register(reg)
        return inst.immediate if inst.immediate is not None else 0

    def execute(self, inst: Instruction, src_val: int, dest_val: int) -> Tuple[int, bool]:
        """执行阶段"""
        result = 0
        write_back = True

        if inst.opcode == 0x1:  # ADD
            result = (dest_val + src_val) & 0xFF
            self.flags.update_add(dest_val, src_val, result)
        elif inst.opcode == 0x2:  # SUB
            result = (dest_val - src_val) & 0xFF
            self.flags.update_sub(dest_val, src_val, result)
        elif inst.opcode == 0x3:  # MUL (逻辑乘)
            result = (dest_val & src_val) & 0xFF
            self.flags.update(result)
        elif inst.opcode == 0x4:  # INC
            result = (dest_val + 1) & 0xFF
            self.flags.update_add(dest_val, 1, result)
        elif inst.opcode == 0x5:  # DEC
            result = (dest_val - 1) & 0xFF
            self.flags.update_sub(dest_val, 1, result)
        elif inst.opcode == 0x7:  # JMP
            result = src_val
            write_back = False
        elif inst.opcode == 0x8:  # JC
            cond = inst.immediate
            condition_met = False
            if cond == 0:
                condition_met = self.flags.N == 1
            elif cond == 1:
                condition_met = self.flags.Z == 1
            elif cond == 2:
                condition_met = self.flags.C == 1
            elif cond == 3:
                condition_met = self.flags.V == 1

            if condition_met:
                result = src_val
                write_back = False
            else:
                write_back = False
        elif inst.opcode == 0xA:  # MOV
            result = src_val
        elif inst.opcode == 0xE:  # LDI
            result = inst.immediate
        elif inst.opcode == 0x9:  # LD
            result = self.data_memory[inst.immediate]
        elif inst.opcode == 0xF:  # ST
            self.data_memory[self.registers[7]] = src_val
            write_back = False
        else:  # NOP
            write_back = False

        return result, write_back

    def step(self) -> bool:
        """单步执行"""
        if self.halted:
            return False

        # 写回阶段
        ex_data = self.pipeline_regs[PipelineStage.EX]
        if ex_data['result'] is not None and ex_data['dest_addr'] is not None:
            self.write_register(ex_data['dest_addr'], ex_data['result'])

        # 流水线推进: EX <- DR
        dr_data = self.pipeline_regs[PipelineStage.DR]
        self.pipeline_regs[PipelineStage.EX] = {
            'instruction': dr_data['instruction'],
            'result': None,
            'dest_addr': dr_data['dest_addr'],
            'pc': dr_data['pc']
        }

        # 流水线推进: DR <- OR
        or_data = self.pipeline_regs[PipelineStage.OR]
        dest_val = None
        if or_data['instruction']:
            dest_val = self.read_operand(or_data['instruction'], is_src=False)

        self.pipeline_regs[PipelineStage.DR] = {
            'instruction': or_data['instruction'],
            'src_val': or_data['src_val'],
            'dest_val': dest_val,
            'dest_addr': or_data['dest_addr'],
            'pc': or_data['pc']
        }

        # 流水线推进: OR <- ID
        id_data = self.pipeline_regs[PipelineStage.ID]
        src_val = None
        dest_addr = None
        if id_data['decoded_inst']:
            src_val = self.read_operand(id_data['decoded_inst'], is_src=True)
            dest_addr = id_data['decoded_inst'].dest_reg

        self.pipeline_regs[PipelineStage.OR] = {
            'instruction': id_data['decoded_inst'],
            'src_val': src_val,
            'dest_addr': dest_addr,
            'pc': id_data['pc']
        }

        # 流水线推进: ID <- IF
        if_data = self.pipeline_regs[PipelineStage.IF]
        decoded = None
        if if_data['instruction'] is not None:
            decoded = self.decode(if_data['instruction'])

        self.pipeline_regs[PipelineStage.ID] = {
            'instruction': if_data['instruction'],
            'decoded_inst': decoded,
            'pc': if_data['pc']
        }

        # 取指阶段
        next_inst = self.fetch()
        self.pipeline_regs[PipelineStage.IF] = {
            'instruction': next_inst,
            'pc': self.pc - 2 if next_inst is not None else self.pc
        }

        # 执行阶段
        dr_to_ex = self.pipeline_regs[PipelineStage.DR]
        if dr_to_ex['instruction']:
            result, write_back = self.execute(
                dr_to_ex['instruction'],
                dr_to_ex['src_val'],
                dr_to_ex['dest_val']
            )
            if write_back:
                self.pipeline_regs[PipelineStage.EX]['result'] = result
                self.pipeline_regs[PipelineStage.EX]['dest_addr'] = dr_to_ex['instruction'].dest_reg

        self.cycle_count += 1
        self._log_cycle()

        # 检查是否结束
        if next_inst is None and all(self.pipeline_regs[i]['instruction'] is None for i in range(5)):
            self.halted = True

        return not self.halted

    def _log_cycle(self):
        """记录周期日志"""
        log_entry = {
            'cycle': self.cycle_count,
            'pc': self.pc,
            'registers': self.registers.copy(),
            'flags': str(self.flags),
            'pipeline': {}
        }
        for stage in range(5):
            inst = self.pipeline_regs[stage]['instruction']
            if inst:
                if isinstance(inst, Instruction):
                    log_entry['pipeline'][stage] = str(inst)
                else:
                    log_entry['pipeline'][stage] = f"0x{inst:04X}" if inst else "----"
            else:
                log_entry['pipeline'][stage] = "----"
        self.cycle_log.append(log_entry)

    def run(self, max_steps: int = 1000):
        """连续运行"""
        steps = 0
        while steps < max_steps and not self.halted:
            self.step()
            steps += 1

    def get_pipeline_display(self) -> List[str]:
        """获取流水线显示"""
        display = []
        for stage in range(5):
            inst = self.pipeline_regs[stage]['instruction']
            if inst:
                if isinstance(inst, Instruction):
                    display.append(str(inst))
                else:
                    display.append(f"0x{inst:04X}" if inst else "空")
            else:
                display.append("空")
        return display

    def get_current_instruction(self) -> str:
        """获取当前执行指令"""
        ex_inst = self.pipeline_regs[PipelineStage.EX]['instruction']
        if ex_inst and isinstance(ex_inst, Instruction):
            return str(ex_inst)
        return "无"


class ModelMachineGUI:
    """图形界面类"""

    def __init__(self):
        self.machine = ModelMachine()
        self.running = False
        self.auto_step = False

        self.root = tk.Tk()
        self.root.title("计算机模型机模拟器 - 5级流水线 | 计算机组成原理课程设计")
        self.root.geometry("1400x950")
        self.root.configure(bg='#2b2b2b')

        self.setup_ui()

        # 创建默认测试程序
        self.create_test_program()
        self.machine.load_program("test.data")
        self.update_display()

    def setup_ui(self):
        """设置UI界面"""
        # 样式配置
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('微软雅黑', 16, 'bold'), foreground='white', background='#2b2b2b')
        style.configure('Header.TLabel', font=('微软雅黑', 12, 'bold'), foreground='#4CAF50', background='#2b2b2b')
        style.configure('Info.TLabel', font=('Consolas', 10), foreground='white', background='#2b2b2b')
        style.configure('Red.TLabel', foreground='#ff6b6b', background='#2b2b2b')
        style.configure('Green.TLabel', foreground='#4CAF50', background='#2b2b2b')
        style.configure('Yellow.TLabel', foreground='#FFD93D', background='#2b2b2b')

        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=0)

        # 标题
        title_label = ttk.Label(main_frame, text="计算机模型机模拟器 - 5级流水线架构", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # 左侧面板 - 寄存器
        self._create_register_panel(main_frame)

        # 中间面板 - 流水线
        self._create_pipeline_panel(main_frame)

        # 右侧面板 - 存储器
        self._create_memory_panel(main_frame)

        # 底部面板 - 日志
        self._create_log_panel(main_frame)

        # 菜单栏
        self._create_menu()

    def _create_register_panel(self, parent):
        """创建寄存器面板"""
        left_frame = ttk.LabelFrame(parent, text="寄存器与状态", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # 通用寄存器
        ttk.Label(left_frame, text="通用寄存器 (8位)", style='Header.TLabel').grid(row=0, column=0, columnspan=4,
                                                                                   pady=(0, 10))

        self.reg_labels = []
        for i in range(8):
            ttk.Label(left_frame, text=f"r{i}:", style='Info.TLabel', width=4).grid(row=i + 1, column=0, padx=5, pady=2)
            reg_val = ttk.Label(left_frame, text="00", style='Yellow.TLabel', font=('Consolas', 11, 'bold'), width=6)
            reg_val.grid(row=i + 1, column=1, padx=5, pady=2)
            reg_dec = ttk.Label(left_frame, text="0", style='Info.TLabel', width=8)
            reg_dec.grid(row=i + 1, column=2, padx=5, pady=2)
            self.reg_labels.append((reg_val, reg_dec))

        # 标志位
        ttk.Label(left_frame, text="状态寄存器", style='Header.TLabel').grid(row=9, column=0, columnspan=4,
                                                                             pady=(15, 10))

        self.flag_labels = {}
        flags = [('V', '有符号溢出'), ('C', '进位/借位'), ('N', '负数'), ('Z', '零')]
        for i, (flag, desc) in enumerate(flags):
            ttk.Label(left_frame, text=f"{flag}:", style='Info.TLabel', width=4).grid(row=10, column=i * 2, padx=5)
            flag_label = ttk.Label(left_frame, text="0", style='Green.TLabel', font=('Consolas', 11, 'bold'), width=4)
            flag_label.grid(row=10, column=i * 2 + 1, padx=5)
            self.flag_labels[flag] = flag_label

        # PC寄存器
        ttk.Label(left_frame, text="PC:", style='Info.TLabel', width=4).grid(row=11, column=0, padx=5, pady=(15, 5))
        self.pc_label = ttk.Label(left_frame, text="0000", style='Red.TLabel', font=('Consolas', 12, 'bold'), width=8)
        self.pc_label.grid(row=11, column=1, padx=5, pady=(15, 5))

        # 控制按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=12, column=0, columnspan=4, pady=(20, 0))

        ttk.Button(button_frame, text="◀ 单步执行", command=self.step, width=12).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="▶ 运行", command=self.run, width=12).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="⏸ 暂停", command=self.pause, width=12).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="↺ 复位", command=self.reset, width=12).pack(side=tk.LEFT, padx=3)

        # 额外信息
        info_frame = ttk.Frame(left_frame)
        info_frame.grid(row=13, column=0, columnspan=4, pady=(20, 0))

        ttk.Label(info_frame, text="指令集: ADD, SUB, MUL, INC, DEC", style='Info.TLabel').pack()
        ttk.Label(info_frame, text="JMP, JC, MOV, LDI, LD, ST, NOP", style='Info.TLabel').pack()

    def _create_pipeline_panel(self, parent):
        """创建流水线面板"""
        middle_frame = ttk.LabelFrame(parent, text="5级流水线状态", padding="10")
        middle_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10)

        self.pipeline_labels = []
        stage_names = ["取指 (IF) - 从存储器读取指令",
                       "译码 (ID) - 指令译码",
                       "取源操作数 (OR) - 读取源操作数",
                       "取目的操作数 (DR) - 读取目的操作数",
                       "执行 (EX) - ALU运算/写回"]
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]

        for i, (name, color) in enumerate(zip(stage_names, colors)):
            frame = ttk.Frame(middle_frame)
            frame.pack(fill=tk.X, pady=8)

            ttk.Label(frame, text=f"► {name}", style='Header.TLabel', foreground=color).pack(side=tk.LEFT, padx=10)
            inst_label = ttk.Label(frame, text="空", style='Info.TLabel', font=('Consolas', 10), width=40)
            inst_label.pack(side=tk.LEFT, padx=20)
            self.pipeline_labels.append(inst_label)

        # 执行结果
        result_frame = ttk.Frame(middle_frame)
        result_frame.pack(pady=(20, 10))

        ttk.Label(result_frame, text="当前执行指令:", style='Header.TLabel').pack(side=tk.LEFT, padx=5)
        self.current_inst_label = ttk.Label(result_frame, text="无", style='Green.TLabel',
                                            font=('Consolas', 12, 'bold'))
        self.current_inst_label.pack(side=tk.LEFT, padx=10)

        self.cycle_label = ttk.Label(middle_frame, text="周期数: 0", style='Info.TLabel', font=('Consolas', 11))
        self.cycle_label.pack(pady=(10, 0))

    def _create_memory_panel(self, parent):
        """创建存储器面板"""
        right_frame = ttk.LabelFrame(parent, text="数据存储器 (地址0-255)", padding="10")
        right_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))

        # 控制栏
        control_bar = ttk.Frame(right_frame)
        control_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_bar, text="显示范围:").pack(side=tk.LEFT, padx=5)
        self.mem_start = tk.StringVar(value="0")
        self.mem_end = tk.StringVar(value="255")

        ttk.Entry(control_bar, textvariable=self.mem_start, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(control_bar, text="-").pack(side=tk.LEFT)
        ttk.Entry(control_bar, textvariable=self.mem_end, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_bar, text="刷新", command=self.update_memory_display, width=6).pack(side=tk.LEFT, padx=5)

        # 存储器显示
        mem_frame = ttk.Frame(right_frame)
        mem_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(mem_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.memory_text = tk.Text(mem_frame, height=22, width=45, font=('Consolas', 9),
                                   bg='#1e1e1e', fg='#d4d4d4', insertbackground='white',
                                   yscrollcommand=scrollbar.set)
        self.memory_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.memory_text.yview)

    def _create_log_panel(self, parent):
        """创建日志面板"""
        bottom_frame = ttk.LabelFrame(parent, text="执行日志", padding="10")
        bottom_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        # 日志控制栏
        log_control = ttk.Frame(bottom_frame)
        log_control.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(log_control, text="清空日志", command=self.clear_log, width=10).pack(side=tk.RIGHT, padx=5)

        self.log_text = scrolledtext.ScrolledText(bottom_frame, height=8, font=('Consolas', 9),
                                                  bg='#1e1e1e', fg='#d4d4d4')
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="加载程序...", command=self.load_program)
        file_menu.add_command(label="重新加载测试程序", command=self.reload_test_program)
        file_menu.add_separator()
        file_menu.add_command(label="导出日志...", command=self.export_log)
        file_menu.add_command(label="导出存储器...", command=self.export_memory)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 运行菜单
        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="运行", menu=run_menu)
        run_menu.add_command(label="单步执行 (F5)", command=self.step)
        run_menu.add_command(label="连续运行 (F6)", command=self.run)
        run_menu.add_command(label="暂停 (F7)", command=self.pause)
        run_menu.add_command(label="复位 (F8)", command=self.reset)

        # 演示菜单
        demo_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="演示", menu=demo_menu)
        demo_menu.add_command(label="排序演示", command=self.sort_demo)
        demo_menu.add_command(label="指令集测试", command=self.instruction_test)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)

    def create_test_program(self):
        """创建测试程序"""
        test_code = """; ============================================
; 模型机测试程序
; 演示所有指令的功能
; ============================================

; 初始化寄存器
ldi r0, 10     ; r0 = 10
ldi r1, 5      ; r1 = 5
ldi r2, 0      ; r2 = 0
ldi r3, 0      ; r3 = 0
ldi r4, 0      ; r4 = 0
ldi r5, 0      ; r5 = 0
ldi r6, 0      ; r6 = 0
ldi r7, 0      ; r7 = 0 (间接寻址指针)

; ========== 算术运算测试 ==========
add r2, r0     ; r2 = r0 + r1 = 10 + 5 = 15
add r2, r1     ; r2 = 15 + 5 = 20

sub r3, r0     ; r3 = r0 - r1 = 10 - 5 = 5
sub r3, r1     ; r3 = 5 - 5 = 0

mul r4, r0     ; r4 = r0 & r1 = 10 & 5 = 0

; ========== 自增自减测试 ==========
inc r0         ; r0 = 11
dec r0         ; r0 = 10
inc r1         ; r1 = 6
dec r1         ; r1 = 5

; ========== 数据传送测试 ==========
mov r5, r0     ; r5 = r0 = 10
mov r6, r1     ; r6 = r1 = 5

; ========== 存储器操作测试 ==========
ldi r7, 100    ; 设置指针地址
st 100, r5     ; 将r5的值存储到地址100
ld r7, 100     ; 从地址100装载到r7

; ========== 条件跳转测试 ==========
ldi r0, 0
jc r0          ; 如果进位标志为1则跳转 (不跳转)

; ========== 循环测试 ==========
ldi r0, 5      ; 循环计数
ldi r1, 1      ; 初始值
ldi r2, 0      ; 累加结果

loop:
add r2, r1     ; 累加
inc r1         ; 值加1
dec r0         ; 计数减1
jc r0          ; 如果r0不为0则继续 (这里用JC检查Z标志)
jmp loop       ; 无条件跳转

continue:
nop
nop

; ========== 程序结束 ==========
halt:
jmp halt
"""
        with open("test.data", 'w', encoding='utf-8') as f:
            f.write(test_code)

    def reload_test_program(self):
        """重新加载测试程序"""
        self.create_test_program()
        self.machine.load_program("test.data")
        self.reset()
        self.add_log("测试程序已重新加载")
        messagebox.showinfo("成功", "测试程序已重新加载")

    def load_program(self):
        """加载用户程序"""
        filename = filedialog.askopenfilename(
            title="选择程序文件",
            filetypes=[("汇编文件", "*.data"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            if self.machine.load_program(filename):
                self.reset()
                self.add_log(f"程序加载成功: {filename}")
                messagebox.showinfo("成功", f"程序加载成功: {filename}")
            else:
                messagebox.showerror("错误", "程序加载失败，请检查文件格式")

    def update_display(self):
        """更新所有显示"""
        # 更新寄存器
        for i in range(8):
            val = self.machine.registers[i]
            self.reg_labels[i][0].config(text=f"{val:02X}")
            self.reg_labels[i][1].config(text=f"{val:3d}")

        # 更新标志位
        self.flag_labels['V'].config(text=str(self.machine.flags.V))
        self.flag_labels['C'].config(text=str(self.machine.flags.C))
        self.flag_labels['N'].config(text=str(self.machine.flags.N))
        self.flag_labels['Z'].config(text=str(self.machine.flags.Z))

        # 更新PC
        self.pc_label.config(text=f"{self.machine.pc:04X}")

        # 更新流水线
        pipeline_display = self.machine.get_pipeline_display()
        for i, display in enumerate(pipeline_display):
            self.pipeline_labels[i].config(text=display)

        # 更新当前指令
        self.current_inst_label.config(text=self.machine.get_current_instruction())

        # 更新周期数
        self.cycle_label.config(text=f"周期数: {self.machine.cycle_count}")

    def update_memory_display(self):
        """更新存储器显示"""
        try:
            start = int(self.mem_start.get())
            end = min(int(self.mem_end.get()), 65535)
        except:
            start, end = 0, 255

        self.memory_text.delete(1.0, tk.END)

        for addr in range(start, end + 1, 16):
            line = f"{addr:04X}: "
            for i in range(16):
                if addr + i <= end:
                    val = self.machine.data_memory[addr + i]
                    line += f"{val:02X} "
                else:
                    line += "   "
            line += "\n"
            self.memory_text.insert(tk.END, line)

    def add_log(self, message: str):
        """添加日志"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

        # 限制日志长度
        if float(self.log_text.index('end-1c')) > 1000:
            self.log_text.delete(1.0, 500.0)

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.add_log("日志已清空")

    def step(self):
        """单步执行"""
        if not self.machine.halted:
            self.machine.step()
            self.update_display()
            self.update_memory_display()

            # 添加日志
            if self.machine.cycle_log:
                last_log = self.machine.cycle_log[-1]
                self.add_log(f"周期{last_log['cycle']:3d}: "
                             f"PC={last_log['pc']:04X} | "
                             f"IF:{last_log['pipeline'][0]} | "
                             f"EX:{last_log['pipeline'][4]}")

            if self.machine.halted:
                self.add_log("=" * 50)
                self.add_log("程序执行完毕")
                self.auto_step = False
        else:
            self.add_log("程序已停止，请先复位")

    def run(self):
        """运行"""
        if self.machine.halted:
            self.reset()
        self.auto_step = True
        self.add_log("开始连续执行...")
        self._auto_run()

    def _auto_run(self):
        """自动运行"""
        if self.auto_step and not self.machine.halted:
            self.step()
            self.root.after(100, self._auto_run)
        elif self.machine.halted:
            self.auto_step = False

    def pause(self):
        """暂停"""
        self.auto_step = False
        self.add_log("执行已暂停")

    def reset(self):
        """复位"""
        self.machine.reset()
        self.auto_step = False
        self.update_display()
        self.update_memory_display()
        self.add_log("系统已复位")

    def export_log(self):
        """导出日志"""
        filename = filedialog.asksaveasfilename(
            title="保存日志",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("计算机模型机执行日志\n")
                f.write("=" * 80 + "\n\n")

                for log in self.machine.cycle_log:
                    f.write(f"周期 {log['cycle']:4d}\n")
                    f.write(f"  PC: {log['pc']:04X}\n")
                    f.write(f"  标志位: {log['flags']}\n")
                    f.write(f"  寄存器: ")
                    for i in range(8):
                        f.write(f"r{i}={log['registers'][i]:02X} ")
                    f.write("\n")
                    f.write(f"  流水线:\n")
                    f.write(f"    IF: {log['pipeline'][0]}\n")
                    f.write(f"    ID: {log['pipeline'][1]}\n")
                    f.write(f"    OR: {log['pipeline'][2]}\n")
                    f.write(f"    DR: {log['pipeline'][3]}\n")
                    f.write(f"    EX: {log['pipeline'][4]}\n")
                    f.write("\n")

            self.add_log(f"日志已导出到: {filename}")
            messagebox.showinfo("成功", f"日志已保存到: {filename}")

    def export_memory(self):
        """导出存储器"""
        filename = filedialog.asksaveasfilename(
            title="保存存储器",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("数据存储器内容\n")
                f.write("=" * 80 + "\n\n")

                for addr in range(0, 256, 16):
                    f.write(f"{addr:04X}: ")
                    for i in range(16):
                        f.write(f"{self.machine.data_memory[addr + i]:02X} ")
                    f.write("\n")

            self.add_log(f"存储器已导出到: {filename}")
            messagebox.showinfo("成功", f"存储器已保存到: {filename}")

    def sort_demo(self):
        """排序演示"""
        # 暂停当前执行
        self.auto_step = False

        # 准备数据
        data = [5, 2, 8, 1, 9, 3, 7, 4, 6]

        # 将数据存入存储器
        for i, value in enumerate(data):
            self.machine.data_memory[i] = value

        self.update_memory_display()
        self.add_log(f"排序前数据: {data}")

        # 冒泡排序
        n = len(data)
        steps = 0
        for i in range(n - 1):
            for j in range(n - 1 - i):
                a = self.machine.data_memory[j]
                b = self.machine.data_memory[j + 1]
                if a > b:
                    self.machine.data_memory[j] = b
                    self.machine.data_memory[j + 1] = a
                    steps += 1

        sorted_data = [self.machine.data_memory[i] for i in range(len(data))]
        self.update_memory_display()
        self.add_log(f"排序后数据: {sorted_data}")
        self.add_log(f"排序完成，共交换 {steps} 次")

        messagebox.showinfo("排序演示",
                            f"排序完成！\n\n"
                            f"原始数据: {data}\n"
                            f"排序结果: {sorted_data}\n"
                            f"交换次数: {steps}")

    def instruction_test(self):
        """指令集测试"""
        test_window = tk.Toplevel(self.root)
        test_window.title("指令集测试")
        test_window.geometry("800x600")
        test_window.configure(bg='#2b2b2b')

        text_area = scrolledtext.ScrolledText(test_window, font=('Consolas', 10),
                                              bg='#1e1e1e', fg='#d4d4d4')
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        test_info = """
=== 模型机指令集说明 ===

1. ADD Rd, Rs - 加法指令
   功能: Rd <- Rd + Rs
   影响标志位: Z, C, N, V
   机器码: 0001 000ddd 000sss

2. SUB Rd, Rs - 减法指令
   功能: Rd <- Rd - Rs
   影响标志位: Z, C, N, V
   机器码: 0010 000ddd 000sss

3. MUL Rd, Rs - 逻辑乘指令
   功能: Rd <- Rd & Rs
   影响标志位: Z, C, N
   机器码: 0011 000ddd 000sss

4. INC Rd - 加1指令
   功能: Rd <- Rd + 1
   影响标志位: Z, C, N, V
   机器码: 0100 000ddd ******

5. DEC Rd - 减1指令
   功能: Rd <- Rd - 1
   影响标志位: Z, C, N, V
   机器码: 0101 000ddd ******

6. JMP Rd - 无条件跳转
   功能: PC <- Rd
   机器码: 0111 kkkk kkkk kddd

7. JC Rd - 条件跳转
   功能: if (条件) PC <- Rd
   条件: 00:N, 01:Z, 10:C, 11:V
   机器码: 1000 000ddd ****00

8. MOV Rd, Rs - 数据传送
   功能: Rd <- Rs
   机器码: 1010 000ddd 000sss

9. LDI Rd, K - 加载立即数
   功能: Rd <- K
   机器码: 1110 KKKK KKKK 0ddd

10. LD Rd, K - 加载存储器
    功能: Rd <- (K)
    机器码: 1001 KKKK KKKK 1ddd

11. ST X, Rs - 存储指令
    功能: (X) <- Rs, X默认为R7
    机器码: 1111 **** **000sss

12. NOP - 空操作
    机器码: 0000 0000 0000 0000

=== 寻址方式 ===
000: 寄存器寻址
001: 寄存器间址
010: 自增型间址
011: 自增型双间址

=== 状态寄存器格式 ===
位7: V - 有符号溢出
位6: C - 无符号进位/借位
位5: N - 负数
位4: Z - 零

=== 统一编址 ===
地址0-7: 通用寄存器r0-r7
地址8: 状态寄存器SR
地址9-65535: 数据存储器
"""
        text_area.insert(tk.END, test_info)
        text_area.config(state=tk.DISABLED)

    def show_help(self):
        """显示帮助"""
        help_text = """使用说明

1. 加载程序
   - 点击"文件" -> "加载程序" 选择汇编文件
   - 汇编文件格式：每行一条指令
   - 支持标签和注释（以;开头）

2. 执行程序
   - 单步执行：逐条执行指令，观察流水线变化
   - 连续运行：自动执行直到程序结束
   - 暂停：暂停连续执行
   - 复位：重置所有状态

3. 查看状态
   - 左侧：寄存器值、标志位、PC
   - 中间：5级流水线当前内容
   - 右侧：数据存储器内容
   - 底部：执行日志

4. 导出数据
   - 导出日志：保存完整的执行记录
   - 导出存储器：保存数据存储器内容

5. 演示功能
   - 排序演示：展示冒泡排序算法
   - 指令集测试：查看指令说明

快捷键：
  F5 - 单步执行
  F6 - 连续运行
  F7 - 暂停
  F8 - 复位
"""
        messagebox.showinfo("使用说明", help_text)

    def show_about(self):
        """显示关于"""
        about_text = """计算机模型机模拟器 v2.0

计算机组成原理课程设计

特性：
• 5级流水线 (IF, ID, OR, DR, EX)
• 12条基本指令
• 统一编址 (寄存器与存储器)
• 4个状态标志位 (V, C, N, Z)
• 可视化流水线状态
• 单步/连续执行模式

设计要求：
• 指令存储器16位，数据存储器8位
• 指令和数据存储器分离
• 5级流水线架构
• 支持寄存器寻址和间接寻址

技术栈：
• Python 3
• Tkinter GUI

© 2024 计算机组成原理课程设计
"""
        messagebox.showinfo("关于", about_text)

    def run_gui(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    gui = ModelMachineGUI()
    gui.run_gui()


if __name__ == "__main__":
    main()

    ###1234