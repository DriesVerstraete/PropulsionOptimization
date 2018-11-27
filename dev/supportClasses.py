import numpy as np
import copy
from scipy import integrate
import scipy.interpolate as interp
import os
from os import path
import matplotlib.pyplot as plt
import polyFit as fit
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from skaero.atmosphere import coesa
import sqlite3 as sql
from random import randint

#Classes in this file are defined such that their information is retrieved from the database (a database cursor must be given).
#If the component's exact name or id are given, that component will be selected. If the manufacturer is given,
#a random component from that manufacturer will be selected. If nothing is specified, a random component is selected.
#The number of battery cells should be specified. If not, it will be randomly selected.

#Converts rads per second to rpms
def toRPM(rads):
    return rads*30/np.pi
    
#A class that defines a battery
class Battery:

    #Initialize the class from database
    def __init__(self, dbcur, name=None, manufacturer=None, dbid=None, numCells=None):

        if name is not None:
            if manufacturer is not None or dbid is not None:
                raise ValueError("Too many battery parameters specified.")
            dbcur.execute("select * from Batteries where Name = '"+name+"'")
        elif manufacturer is not None:
            if dbid is not None:
                raise ValueError("Too many battery parameters specified.")
            dbcur.execute("select * from Batteries where manufacturer = '"+manufacturer+"' order by RANDOM() limit 1")
        elif dbid is not None:
            dbcur.execute("select * from Batteries where id = "+str(dbid))
        else:
            dbcur.execute("select * from Batteries order by RANDOM() limit 1")

        record = np.asarray(dbcur.fetchall())[0]

        if numCells is None:
            numCells = randint(1,8)

        #Define members from inputs
        self.n = int(numCells)
        self.cellCap = float(record[4])
        self.cellR = float(record[6])
        self.name = record[1]
        self.manufacturer = record[2]
        self.cellWeight = float(record[5])
        self.iMax = float(record[3])
        self.cellV = float(record[7])

        #Members derived from inputs
        self.V0 = self.cellV * self.n
        self.R = self.cellR * self.n
        self.weight = self.cellWeight*self.n

    def printInfo(self):
        print("Battery:",self.name)
        print("\tManufacturer:",self.manufacturer)
        print("\tCapacity:",self.cellCap)
        print("\tNum Cells:",self.n)
        print("\tVoltage:",self.V0)
        print("\tWeight:",self.weight)

#A class that defines an ESC (Electronic Speed Controller)
class ESC:

    #Initialization of the class from database
    def __init__(self, dbcur, name=None, manufacturer=None, dbid=None):

        if name is not None:
            if manufacturer is not None or dbid is not None:
                raise ValueError("Too many esc parameters specified.")
            dbcur.execute("select * from ESCs where Name = '"+name+"'")
        elif manufacturer is not None:
            if dbid is not None:
                raise ValueError("Too many ESC parameters specified.")
            dbcur.execute("select * from ESCs where manufacturer = '"+manufacturer+"' order by RANDOM() limit 1")
        elif dbid is not None:
            dbcur.execute("select * from ESCs where id = "+str(dbid))
        else:
            dbcur.execute("select * from ESCs order by RANDOM() limit 1")

        record = np.asarray(dbcur.fetchall())[0]

        self.R = float(record[6])
        self.name = record[1]
        self.manufacturer = record[2]
        self.iMax = float(record[3])
        self.weight = float(record[5])

    def printInfo(self):
        print("ESC:",self.name)
        print("\tManufacturer:",self.manufacturer)
        print("\tMax Current:",self.iMax)
        print("\tWeight:",self.weight)
        
#A class that defines an electric motor.
class Motor:

    #Initialization of the class from the database
    def __init__(self, dbcur, name=None, manufacturer=None, dbid=None):

        if name is not None:
            if manufacturer is not None or dbid is not None:
                raise ValueError("Too many motor parameters specified.")
            dbcur.execute("select * from Motors where Name = '"+name+"'")
        elif manufacturer is not None:
            if dbid is not None:
                raise ValueError("Too many motor parameters specified.")
            dbcur.execute("select * from Motors where manufacturer = '"+manufacturer+"' order by RANDOM() limit 1")
        elif dbid is not None:
            dbcur.execute("select * from Motors where id = "+str(dbid))
        else:
            dbcur.execute("select * from Motors order by RANDOM() limit 1")

        record = np.asarray(dbcur.fetchall())[0]

        self.Kv = float(record[3])
        self.Gr = float(record[4])
        self.I0 = float(record[6])
        self.R = float(record[5])
        self.name = record[1]
        self.manufacturer = record[2]
        self.weight = float(record[7])

    def printInfo(self):
        print("Motor:",self.name)
        print("\tManufacturer:",self.manufacturer)
        print("\tKv:",self.Kv)
        print("\tWeight:",self.weight)

#A class of propellers defined by database test files
class Propeller:
    
    #Initializes the prop from the database
    def __init__(self, dbcur, name=None, manufacturer=None, dbid=None):

        if name is not None:
            if manufacturer is not None or dbid is not None:
                raise ValueError("Too many prop parameters specified.")
            dbcur.execute("select * from Props where Name = '"+name+"'")
        elif manufacturer is not None:
            if dbid is not None:
                raise ValueError("Too many prop parameters specified.")
            dbcur.execute("select * from Props where manufacturer = '"+manufacturer+"' order by RANDOM() limit 1")
        elif dbid is not None:
            dbcur.execute("select * from Props where id = "+str(dbid))
        else:
            dbcur.execute("select * from Props order by RANDOM() limit 1")

        record = np.asarray(dbcur.fetchall())[0]

        self.name = record[1]
        self.manufacturer = record[2]
        self.diameter = float(record[3])
        self.pitch = float(record[4])
        self.thrustFitOrder = int(record[5])
        self.fitOfThrustFitOrder = int(record[6])
        self.powerFitOrder = int(record[7])
        self.fitOfPowerFitOrder = int(record[8])

        numThrustCoefs = (self.thrustFitOrder+1)*(self.fitOfThrustFitOrder+1)
        self.thrustCoefs = record[9:numThrustCoefs+9].reshape((self.thrustFitOrder+1,self.fitOfThrustFitOrder+1)).astype(np.float)
        self.powerCoefs = record[numThrustCoefs+9:].reshape((self.powerFitOrder+1,self.fitOfPowerFitOrder+1)).astype(np.float)

        #These parameters will be set by later functions
        self.vInf = 0.0
        self.angVel = 0.0
        
    def printInfo(self):
        print("Propeller:",self.name)
        print("\tManufacturer:",self.manufacturer)
        print("\tDiameter:",self.diameter)
        print("\tPitch:",self.pitch)

    def CalcTorqueCoef(self):
        self.rpm = toRPM(self.angVel)
        self.rps = self.rpm/60
        if abs(self.rps)<1e-10:
            self.J = 10000 #To prevent errors. Since angular velocity is 0, actual value will also be 0.
        else:
            self.J = self.vInf/(self.rps*self.diameter/12)
        a = fit.poly_func(self.powerCoefs.T, self.rpm)
        if(a[-1]>0):#Quadratic coefficient should always be non-positive
            a[-1] = 0
        self.Cl = fit.poly_func(a, self.J)/2*np.pi
        

    def CalcThrustCoef(self):
        self.rpm = toRPM(self.angVel)
        self.rps = self.rpm/60
        if abs(self.rps)<1e-10:
            self.J = 10000 #To prevent errors. Since angular velocity is 0, actual value will also be 0.
        else:
            self.J = self.vInf/(self.rps*self.diameter/12)
        a = fit.poly_func(self.thrustCoefs.T, self.rpm)
        if(a[-1]>0):#Quadratic coefficient should always be non-positive
            a[-1] = 0
        self.Ct = fit.poly_func(a, self.J)

    def PlotCoefs(self):
        #Plot thrust and torque coefficients
        rpms = np.linspace(0,35000,10)
        Js = np.linspace(0,1.4,10)
        fig = plt.figure(figsize=plt.figaspect(1.))
        fig.suptitle(self.name)
        ax = fig.add_subplot(1,2,1, projection='3d')

        for rpm in rpms:
            a = fit.poly_func(self.thrustCoefs.T, rpm)
            if(a[-1]>0):#Quadratic coefficient should always be non-positive
                a[-1] = 0
            thrust = fit.poly_func(a, Js)
            rpmForPlot = np.full(len(thrust),rpm)
            ax.plot(Js,rpmForPlot,thrust, 'r-')

        ax.set_title("Predicted Thrust")
        ax.set_xlabel("Advance Ratio")
        ax.set_ylabel("RPM")
        ax.set_zlabel("Thrust Coefficient")

        ax = fig.add_subplot(1,2,2, projection='3d')

        for rpm in rpms:
            a = fit.poly_func(self.powerCoefs.T, rpm)
            if(a[-1]>0):#Quadratic coefficient should always be non-positive
                a[-1] = 0
            power = fit.poly_func(a, Js)
            rpmForPlot = np.full(len(power),rpm)
            ax.plot(Js,rpmForPlot,power, 'r-')

        ax.set_title("Predicted Power")
        ax.set_xlabel("Advance Ratio")
        ax.set_ylabel("RPM")
        ax.set_zlabel("Power Coefficient")
        plt.show()

#A class that defines an entire electric propulsion unit
class PropulsionUnit:

    #Initialize the class from subclasses which are previously initialized
    def __init__(self, prop, motor, battery, esc, altitude):
        
        self.prop = prop
        self.motor = motor
        self.batt = battery
        self.esc = esc

        _,_,_,self.airDensity = coesa.table(altitude*0.3048) # Converts from ft to m
        self.airDensity = self.airDensity*0.0019403203 # Converts kg/m^3 to slug/ft^3
        
        #Initialize exterior parameters to be set later
        self.prop.vInf = 0
        self.prop.angVel = 0
        self.Im = 0 #Instantaneous current being drawn through the motor

    #Computes motor torque (ft*lbf) given throttle setting and revolutions (rpm)
    def CalcMotorTorque(self, throttle, revs):
        etaS = 1 - 0.078*(1 - throttle)
        self.Im = (etaS*throttle*self.batt.V0 - (self.motor.Gr/self.motor.Kv)*revs)/(etaS*throttle*self.batt.R + self.esc.R + self.motor.R)
        # Note: the 7.0432 constant converts units [(Nm/ftlb)(min/s)(rad/rev)]^-1
        return 7.0432*self.motor.Gr/self.motor.Kv * (self.Im - self.motor.I0)
    
    #Computes thrust produced at a given cruise speed and throttle setting
    def CalcCruiseThrust(self, cruiseSpeed, throttle):
        if cruiseSpeed == 0 and throttle == 0:
            self.prop.angVel = 0
            return 0 #Don't even bother

        self.prop.vInf = cruiseSpeed

        #Determine the shaft angular velocity at which the motor torque and propeller torque are matched
        #Uses a secant method
        errorBound = 0.000001
        approxError = 1 + errorBound #So that it executes at least once
        w0 = 300 #An initial guess of the prop's angular velocity
        self.prop.angVel = w0
        self.prop.CalcTorqueCoef()
        f0 = self.CalcMotorTorque(throttle, toRPM(w0)) - self.prop.Cl*self.airDensity*(w0/(2*np.pi))**2*(self.prop.diameter/12)**5
        w1 = w0 * 1.1
        iterations = 0
        
        while approxError >= errorBound and iterations < 1000:
            iterations = iterations + 1
            self.prop.angVel = w1
            self.prop.CalcTorqueCoef()
            motorTorque = self.CalcMotorTorque(throttle, toRPM(w1))
            propTorque = self.prop.Cl*self.airDensity*(w1/(2*np.pi))**2*(self.prop.diameter/12)**5
            f1 = motorTorque - propTorque
            
            w2 = w1 - (f1*(w0 - w1))/(f0 - f1)
            if w2 < 0: # Prop angular velocity will never be negative even if windmilling
                w2 = 0.000001
            if w2 > self.motor.Kv*self.batt.V0*throttle: #Theoretically the upper limit
                w2 = self.motor.Kv*self.batt.V0*throttle

            approxError = abs((w2 - w1)/w2)
            
            w0 = w1
            f0 = f1
            w1 = w2
    
        if False:#iterations >= 1000:
            print(cruiseSpeed)
            print(throttle)
            w = np.linspace(0,50000,10000)
            Tm = np.zeros(10000)
            Tp = np.zeros(10000)
            for i,wi in enumerate(w):
                self.prop.angVel = wi
                self.prop.CalcTorqueCoef()
                Tm[i] = self.CalcMotorTorque(throttle, toRPM(wi))
                Tp[i] = self.prop.Cl*self.airDensity*(wi/(2*np.pi))**2*(self.prop.diameter/12)**5
            plt.plot(w,Tm)
            plt.plot(w,Tp)
            plt.plot(w,Tm-Tp)
            plt.title("Torque Balance vs Angular Velocity")
            plt.legend(["Motor Torque","Prop Torque","Difference"])
            plt.show()
        
        self.prop.angVel = w2
        self.prop.CalcThrustCoef()
        _ = self.CalcMotorTorque(throttle, toRPM(w2)) # To make sure member variables are fully updated

        return self.prop.Ct*self.airDensity*(w2/(2*np.pi))**2*(self.prop.diameter/12)**4
    
    #Computes required throttle setting for a given thrust and cruise speed
    def CalcCruiseThrottle(self, cruiseSpeed, reqThrust):
        #Uses a secant method
        errorBound = 0.000001
        approxError = 1 + errorBound
        t0 = 0.5
        T0 = self.CalcCruiseThrust(cruiseSpeed, t0)
        t1 = t0*1.1
        iterations = 0
        
        while approxError >= errorBound and iterations < 1000:
            
            iterations = iterations + 1
            T1 = self.CalcCruiseThrust(cruiseSpeed, t1) - reqThrust
            
            t2 = t1 - (T1*(t0 - t1))/(T0 - T1)
            
            approxError = abs((t2 - t1)/t2)
            
            if t2 > 10:
                t2 = 1.1
            elif t2 < -10:
                t2 = -0.1
            t0 = t1
            T0 = T1
            t1 = t2

        #if iterations == 1000:
        #    t = np.linspace(0,1.0,100)
        #    T = np.zeros(100)
        #    for i in range(100):
        #        T[i] = self.CalcCruiseThrust(cruiseSpeed, t[i]) - reqThrust
        #    plt.plot(t,T) 
        #    plt.show()

        if t2 > 1 or t2 < 0:
            return None
        
        self.CalcCruiseThrust(cruiseSpeed,t2) # To make sure member variables are fully updated
        return t2
        
    #Plots thrust curves for propulsion unit up to a specified airspeed
    def PlotThrustCurves(self, maxAirspeed, numVels, numThrSets):
        
        vel = np.linspace(0, maxAirspeed, numVels)
        thr = np.linspace(0, 1, numThrSets)
        thrust = np.zeros((numVels, numThrSets))
        rpm = np.zeros((numVels,numThrSets))
        
        for i in range(numVels):
            for j in range(numThrSets):
                
                #print("Freestream Velocity: ", vel[i])
                #print("Throttle Setting: ", thr[j])
                thrust[i][j] = self.CalcCruiseThrust(vel[i], thr[j])
                rpm[i][j] = toRPM(self.prop.angVel)

        fig = plt.figure()
        fig.suptitle("Components: " + str(self.prop.name) + ", " + str(self.motor.name) + ", and " + str(self.batt.name))

        ax0 = fig.add_subplot(1,2,1)
        for i in range(numVels):
            ax0.plot(thr, thrust[i])
        ax0.set_title("Thrust")
        ax0.set_ylabel("Thrust [lbf]")
        ax0.set_xlabel("Throttle Setting")
        ax0.legend(list(vel), title="Airspeed [ft/s]")

        ax1 = fig.add_subplot(1,2,2)
        for i in range(numVels):
            ax1.plot(thr, rpm[i])
        ax1.set_title("Prop Speed")
        ax1.set_ylabel("Speed [rpms]")
        ax1.set_xlabel("Throttle Setting")
        plt.show()

    #Determines how long the battery will last based on a required thrust and cruise speed
    def CalcBattLife(self, cruiseSpeed, reqThrust):
        throttle = self.CalcCruiseThrottle(cruiseSpeed, reqThrust)
        if(throttle==None or self.Im > self.esc.iMax or self.Im > self.batt.iMax):
            return None
        #print("Throttle Setting:",throttle)
        #print("Current Draw:",self.Im)
        runTime = (self.batt.cellCap/1000)/self.Im*60 # Gives run time in minutes, assuming nominal cell capacity and constant battery votlage
        if runTime < 0:
            return None
        return runTime

    def GetWeight(self):#Returns weight of electrical components in pounds
        return (self.batt.weight + self.motor.weight + self.esc.weight)/16

    def printInfo(self):
        print("----Propulsion Unit----")
        self.prop.printInfo()
        self.motor.printInfo()
        self.esc.printInfo()
        self.batt.printInfo()
