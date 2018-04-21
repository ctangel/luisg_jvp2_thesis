from central import application
import subprocess as sp
output  = sp.check_output("ps", shell=True)
running = False
for i in output.split("\n"):
    if "runbase.py" in i:
        running = True
if not running:
    sp.Popen("cd run && python runbase.py", shell=True)
 


if __name__ == "__main__":
  application.run()
