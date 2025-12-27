import abc
import subprocess
import os
from typing import List, Dict, Optional

class Simulator(abc.ABC):
    def __init__(self, name: str, executable: str):
        self.name = name
        self.executable = executable
        self.defines = []
        self.filelists = []
        self.sim_args = []
        self.compile_args = []
        self.elab_args = []
        self.uvm = False
        self.vhdl_file = None
        self.logfile = "run.log"
        self.outdir = "."
        self.filter = None
        self.list_tests = False

    def set_options(self, defines: List[str], filelists: List[str], sim_args: List[str], 
                    compile_args: List[str], elab_args: List[str], uvm: bool, 
                    vhdl_file: str, logfile: str, outdir: str, filter: str, list_tests: bool):
        self.defines = defines if defines else []
        self.filelists = filelists if filelists else []
        self.sim_args = sim_args if sim_args else []
        self.compile_args = compile_args if compile_args else []
        self.elab_args = elab_args if elab_args else []
        self.uvm = uvm
        self.vhdl_file = vhdl_file
        self.logfile = logfile
        self.outdir = outdir
        self.filter = filter
        self.list_tests = list_tests

    @abc.abstractmethod
    def run(self) -> bool:
        """
        Constructs and runs the simulation command.
        Returns True if successful, False otherwise.
        """
        pass

    def _run_command(self, cmd: str) -> bool:
        print(f"Running: {cmd}")
        # Using shell=True to handle complex command chaining (&&, | tee, etc.) similar to Perl script
        # In a more advanced version, we should split this into subprocess calls without shell=True
        ret = subprocess.call(cmd, shell=True, cwd=self.outdir)
        return ret == 0

class ModelSim(Simulator):
    def __init__(self):
        super().__init__("modelsim", "vsim")

    def run(self) -> bool:
        cmd = ""
        cmd += "vlib work && "
        if self.vhdl_file:
            cmd += f"vcom -work work -f {self.vhdl_file} && "
        
        cmd += f"vlog -l {self.logfile} "
        
        if self.uvm:
            self.defines.append("RUN_SVUNIT_WITH_UVM")

        for f in self.filelists:
            cmd += f" -f {f}"
        cmd += " -f .svunit.f"

        if self.defines:
            cmd += " +define+" + "+define+".join(self.defines)

        # Add compile args
        if self.compile_args:
            cmd += " " + " ".join(self.compile_args)

        # Simulation command
        # Check if -c, -gui, or -i is present in sim_args
        has_mode_flag = any(arg in ["-c", "-gui", "-i"] for arg in self.sim_args)
        if not has_mode_flag:
            self.sim_args.append("-c")
        
        vopt_elab_args = f'-voptargs="{" ".join(self.elab_args)}"' if self.elab_args else ""
        
        cmd += f" && vsim {vopt_elab_args} {' '.join(self.sim_args)} -lib work -do \"run -all; quit\" -l {self.logfile} testrunner"
        
        if self.filter:
             cmd += f" +SVUNIT_FILTER={self.filter}"
        
        if self.list_tests:
             cmd += " +SVUNIT_LIST_TESTS"

        return self._run_command(cmd)

class Irun(Simulator):
    def __init__(self):
        super().__init__("irun", "irun")

    def run(self) -> bool:
        cmd = f"{self.executable} -l {self.logfile} "
        if self.vhdl_file:
            cmd += f"-f {self.vhdl_file} "
        
        if self.uvm:
            cmd += " -uvm"
            self.defines.append("RUN_SVUNIT_WITH_UVM")

        for f in self.filelists:
            cmd += f" -f {f}"
        cmd += " -f .svunit.f"

        if self.defines:
            cmd += " +define+" + "+define+".join(self.defines)

        if self.compile_args:
            cmd += " " + " ".join(self.compile_args)
        if self.elab_args:
            cmd += " " + " ".join(self.elab_args)
        if self.sim_args:
            cmd += " " + " ".join(self.sim_args)
            
        cmd += " -top testrunner"

        if self.filter:
             cmd += f" +SVUNIT_FILTER={self.filter}"
        
        if self.list_tests:
             cmd += " +SVUNIT_LIST_TESTS"

        return self._run_command(cmd)

class Xrun(Irun):
    def __init__(self):
        super().__init__()
        self.name = "xrun"
        self.executable = "xrun"

class Vcs(Simulator):
    def __init__(self):
        super().__init__("vcs", "vcs")

    def run(self) -> bool:
        cmd = f"{self.executable} -R -sverilog -l {self.logfile} "
        if self.vhdl_file:
            cmd += f"-f {self.vhdl_file} "
        
        if self.uvm:
            cmd += " -ntb_opts uvm"
            self.defines.append("RUN_SVUNIT_WITH_UVM")

        for f in self.filelists:
            cmd += f" -f {f}"
        cmd += " -f .svunit.f"

        if self.defines:
            cmd += " +define+" + "+define+".join(self.defines)

        if self.compile_args:
            cmd += " " + " ".join(self.compile_args)
        if self.elab_args:
            cmd += " " + " ".join(self.elab_args)
        if self.sim_args:
            cmd += " " + " ".join(self.sim_args)
            
        cmd += " -top testrunner"

        if self.filter:
             cmd += f" +SVUNIT_FILTER={self.filter}"
        
        if self.list_tests:
             cmd += " +SVUNIT_LIST_TESTS"

        return self._run_command(cmd)

class Verilator(Simulator):
    def __init__(self):
        super().__init__("verilator", "verilator")

    def run(self) -> bool:
        if self.uvm:
            print("Argument error: cannot run Verilator with UVM")
            return False
        if self.vhdl_file:
            print("Argument error: cannot run Verilator with VHDL")
            return False

        cmd = "verilator --binary --top-module testrunner"
        
        if self.compile_args:
            cmd += " " + " ".join(self.compile_args)
        if self.elab_args:
            cmd += " " + " ".join(self.elab_args)

        for f in self.filelists:
            cmd += f" -f {f}"
        cmd += " -f .svunit.f"

        if self.defines:
            cmd += " +define+" + "+define+".join(self.defines)

        # Simulation execution
        sim_args_str = " ".join(self.sim_args) if self.sim_args else ""
        if self.filter:
            sim_args_str += f" +SVUNIT_FILTER={self.filter}"
        if self.list_tests:
            sim_args_str += " +SVUNIT_LIST_TESTS"

        cmd += f" && obj_dir/Vtestrunner {sim_args_str} 2>&1 | tee {self.logfile}"

        return self._run_command(cmd)

class Xsim(Simulator):
    def __init__(self):
        super().__init__("xsim", "xsim")

    def run(self) -> bool:
        # Xsim requires modifying .svunit.f to replace +incdir+ with --include
        # This is a specific behavior from the Perl script
        # We will handle this by creating a temporary file list or modifying it in place?
        # The Perl script does: sed -i 's/\+incdir+/--include /g' $outdir/.svunit.f
        # We should probably do this before running the command.
        
        # Let's modify the file in place for now as per Perl script behavior
        svunit_f_path = os.path.join(self.outdir, ".svunit.f")
        if os.path.exists(svunit_f_path):
            with open(svunit_f_path, 'r') as f:
                content = f.read()
            content = content.replace("+incdir+", "--include ")
            with open(svunit_f_path, 'w') as f:
                f.write(content)

        cmd = ""
        if self.vhdl_file:
            cmd += f"xvhdl -f {self.vhdl_file} && "
        
        cmd += f"xvlog --sv --log {self.logfile} "
        
        if self.uvm:
            cmd += " --lib uvm"
            self.defines.append("RUN_SVUNIT_WITH_UVM")

        for f in self.filelists:
            cmd += f" -f {f}"
        cmd += " -f .svunit.f"

        if self.defines:
            cmd += " " + " ".join([f"--define {d}" for d in self.defines])

        if self.compile_args:
            cmd += " " + " ".join(self.compile_args)
        
        cmd += f" && xelab testrunner"
        if self.elab_args:
            cmd += " " + " ".join(self.elab_args)
            
        cmd += f" && xsim"
        if self.sim_args:
            cmd += " " + " ".join(self.sim_args)
        
        cmd += f" --R --log {self.logfile} testrunner"

        if self.filter:
             cmd += f" --testplusarg SVUNIT_FILTER={self.filter}"
        
        if self.list_tests:
             cmd += " --testplusarg SVUNIT_LIST_TESTS"

        return self._run_command(cmd)

class Dsim(Simulator):
    def __init__(self):
        super().__init__("dsim", "dsim")

    def run(self) -> bool:
        cmd = f"{self.executable} -l {self.logfile} "
        if self.vhdl_file:
            cmd += f"-f {self.vhdl_file} "
        
        if self.uvm:
            cmd += ' +incdir+$UVM_HOME/src $UVM_HOME/src/uvm.sv -sv_lib $UVM_HOME/src/dpi/libuvm_dpi.so'
            self.defines.append("RUN_SVUNIT_WITH_UVM")

        for f in self.filelists:
            cmd += f" -f {f}"
        cmd += " -f .svunit.f"

        if self.defines:
            cmd += " +define+" + "+define+".join(self.defines)

        if self.compile_args:
            cmd += " " + " ".join(self.compile_args)
        if self.elab_args:
            cmd += " " + " ".join(self.elab_args)
        if self.sim_args:
            cmd += " " + " ".join(self.sim_args)
            
        cmd += " -top testrunner"

        if self.filter:
             cmd += f" +SVUNIT_FILTER={self.filter}"
        
        if self.list_tests:
             cmd += " +SVUNIT_LIST_TESTS"

        return self._run_command(cmd)

class Qrun(Simulator):
    def __init__(self):
        super().__init__("qrun", "qrun")

    def run(self) -> bool:
        # Assuming qrun behaves similarly to others, Perl script treats it in the 'else' block
        cmd = f"{self.executable} -l {self.logfile} "
        if self.vhdl_file:
            cmd += f"-f {self.vhdl_file} "
        
        if self.uvm:
            self.defines.append("RUN_SVUNIT_WITH_UVM")

        for f in self.filelists:
            cmd += f" -f {f}"
        cmd += " -f .svunit.f"

        if self.defines:
            cmd += " +define+" + "+define+".join(self.defines)

        if self.compile_args:
            cmd += " " + " ".join(self.compile_args)
        if self.elab_args:
            cmd += " " + " ".join(self.elab_args)
        if self.sim_args:
            cmd += " " + " ".join(self.sim_args)
            
        cmd += " -top testrunner"

        if self.filter:
             cmd += f" +SVUNIT_FILTER={self.filter}"
        
        if self.list_tests:
             cmd += " +SVUNIT_LIST_TESTS"

        return self._run_command(cmd)


def get_simulator(name: str) -> Optional[Simulator]:
    name = name.lower()
    if name == "modelsim" or name == "questa":
        return ModelSim()
    elif name == "irun" or name == "ius":
        return Irun()
    elif name == "xrun" or name == "xcelium":
        return Xrun()
    elif name == "vcs":
        return Vcs()
    elif name == "verilator":
        return Verilator()
    elif name == "xsim":
        return Xsim()
    elif name == "dsim":
        return Dsim()
    elif name == "qrun":
        return Qrun()
    elif name == "riviera":
        # Riviera uses same logic as ModelSim in Perl script
        sim = ModelSim()
        sim.name = "riviera"
        # But executable might be different? Perl script says:
        # if ($simulator eq "modelsim" or $simulator eq "riviera")
        # ... vsim ...
        # So it seems it uses vsim command as well? Or maybe 'riviera' command?
        # The Perl script uses 'vsim' for both.
        return sim
    return None

def detect_simulator() -> Optional[Simulator]:
    # Check PATH for simulators
    sims = ["xrun", "irun", "qrun", "vsim", "vcs", "dsim", "verilator", "xsim"]
    for sim in sims:
        if subprocess.call(f"which {sim} > /dev/null 2>&1", shell=True) == 0:
            # Map executable to simulator name
            if sim == "vsim": return ModelSim()
            if sim == "xrun": return Xrun()
            if sim == "irun": return Irun()
            if sim == "vcs": return Vcs()
            if sim == "verilator": return Verilator()
            if sim == "xsim": return Xsim()
            if sim == "dsim": return Dsim()
            if sim == "qrun": return Qrun()
    return None
