#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "pybind11/functional.h"
#include "ghdl_cohdl_interface.hpp"

namespace py = pybind11;

using ghdl_cohdl_interface::GhdlInterface;
using ghdl_cohdl_interface::VpiObjHandle;
using ghdl_cohdl_interface::VpiCbHandle;
using ghdl_cohdl_interface::BitState;

class ObjectHandle
{
    VpiObjHandle _handle;
public:

    ObjectHandle(VpiObjHandle&& handle)
        : _handle{ std::move(handle) }
    {}

    void put_integer(int val)
    {
        _handle.put_value(val);
    }

    void put_binstr(const std::string& binstr)
    {
        _handle.put_value(binstr);
    }

    std::string get_binstr()
    {
        return _handle.get_binstr();
    }

    VpiObjHandle& handle()
    {
        return _handle;
    }
};

class InterfaceWrapper
{
    GhdlInterface& _interface;

public:

    InterfaceWrapper()
        : _interface{ GhdlInterface::singleton() }
    {}

    void start(std::string simulationPath, std::vector<std::string> args)
    {
        _interface.start(simulationPath, args);
    }

    void stop()
    {
        _interface.stop();
    }

    void addStartupFunction(std::function<void()> fn)
    {
        _interface.addStartupFunction(std::move(fn));
    }

    VpiCbHandle callbackDelay(std::function<void()> fn, unsigned delay)
    {
        return _interface.callback_delay(delay, std::move(fn));
    }

    VpiCbHandle callbackValueChange(ObjectHandle& handle, std::function<void()> fn)
    {
        return _interface.callback_value_change(handle.handle(), std::move(fn));
    }

    VpiCbHandle callbackNextSimTime(std::function<void()> fn)
    {
        return _interface.callback_next_sim_time(std::move(fn));
    }

    void cleanup()
    {
        _interface.clearStartupFunctions();
    }

    void finishSimulation()
    {
        cleanup();
        _interface.finish_simulation();
    }

    ObjectHandle handleByName(std::string name)
    {
        return _interface.handle_by_name(name);
    }

    ~InterfaceWrapper()
    {
        _interface.clearStartupFunctions();
    }
};

void enterCallbackHandle(VpiCbHandle& callback)
{}

void exitCallbackHandle(VpiCbHandle& callback, py::object&, py::object&, py::object&)
{
    callback.release();
}


PYBIND11_MODULE(cohdl_sim_ghdl_interface, m) {
    m.doc() = "pybind11 example plugin"; // optional module docstring

    pybind11::class_<VpiCbHandle>(m, "VpiCbHandle")
        .def("release", &VpiCbHandle::release)
        .def("__enter__", enterCallbackHandle)
        .def("__exit__", exitCallbackHandle);

    pybind11::class_<ObjectHandle>(m, "ObjHandle")
        .def("put_integer", &ObjectHandle::put_integer)
        .def("put_binstr", &ObjectHandle::put_binstr)
        .def("get_binstr", &ObjectHandle::get_binstr);

    pybind11::class_<InterfaceWrapper>(m, "GhdlInterface")
        .def(pybind11::init<>())
        .def("handle_by_name", &InterfaceWrapper::handleByName)
        .def("add_startup_function", &InterfaceWrapper::addStartupFunction)
        .def("add_callback_delay", &InterfaceWrapper::callbackDelay)
        .def("add_callback_value_change", &InterfaceWrapper::callbackValueChange)
        .def("add_callback_next_sim_time", &InterfaceWrapper::callbackNextSimTime)
        .def("cb_delay", &InterfaceWrapper::callbackDelay)
        .def("cb_value_change", &InterfaceWrapper::callbackValueChange)
        .def("cb_next_sim_time", &InterfaceWrapper::callbackNextSimTime)
        .def("start", &InterfaceWrapper::start)
        .def("stop", &InterfaceWrapper::stop)
        .def("cleanup", &InterfaceWrapper::cleanup)
        .def("finish_simulation", &InterfaceWrapper::finishSimulation);
}
