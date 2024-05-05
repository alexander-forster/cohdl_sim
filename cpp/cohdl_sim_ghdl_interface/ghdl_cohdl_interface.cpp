#include "ghdl_cohdl_interface.hpp"

#include "ghdl/vpi_user.h"

#include <dlfcn.h>
#include <link.h>

#include <mutex>

void (*vlog_startup_routines[])(void) = {
    ghdl_cohdl_interface::ghdlInterfaceStartup,
    0
};

namespace ghdl_cohdl_interface
{
    int main_signature(int, char**);

    struct VpiFunctions
    {
        decltype(main_signature)* ghdl_main;
        decltype(vpi_put_value)* put_value;
        decltype(vpi_get_value)* get_value;

        decltype(vpi_handle_by_name)* handle_by_name;
        decltype(vpi_register_cb)* register_cb;
        decltype(vpi_free_object)* free_object;
        decltype(vpi_remove_cb)* remove_cb;
        decltype(vpi_control)* control;
    };

    namespace
    {
        template<typename T>
        void load_symbol(void* handle, std::string name, T*& target)
        {
            target = (T*) ::dlsym(handle, name.c_str());

            if (target == nullptr)
            {
                throw std::runtime_error(std::string("dlsym failed to lookup '") + name + "' with error " + ::dlerror());
            }
        }
    }

    //
    //
    //

    VpiHandle::VpiHandle(void* handle, GhdlInterface& interface)
        : _handle{ handle }
        , _interface{ interface }
        , _interfaceId{ interface.id() }
    {
        if (handle == nullptr)
            throw std::runtime_error{ "handle was nullptr" };
    }

    VpiHandle::VpiHandle(VpiHandle&& other)
        : VpiHandle{ other._handle.ptr(), other._interface }
    {
        other._handle = nullptr;
    }

    AnyPtr VpiHandle::get() const noexcept
    {
        return _handle;
    }

    unsigned VpiHandle::interfaceId() const noexcept
    {
        return _interfaceId;
    }

    std::uintptr_t VpiHandle::id() const noexcept
    {
        return _handle.id();
    }

    VpiHandle::~VpiHandle()
    {
        if (_handle.ptr() != nullptr)
        {
            _interface._clearHandle(*this);
        }
    }

    //
    //
    //

    void VpiObjHandle::put_value(BitState state)
    {
        _interface.put_value(*this, state);
    }

    void VpiObjHandle::put_value(const std::string& binstr)
    {
        _interface.put_value(*this, binstr);
    }

    void VpiObjHandle::put_value(int intValue)
    {
        _interface.put_value(*this, intValue);
    }

    std::string VpiObjHandle::get_binstr() const
    {
        return _interface.get_binstr(*this);
    }

    //
    //
    //

    void VpiCbHandle::release()
    {
        if (_handle.ptr() != nullptr)
        {
            if (_removeRequired)
            {
                _interface._removeCallback(*this, _callback);

                // clear handle so it is not released by the destructor
                // of VpiHandle
                _handle.clear();
            }
        }
    }

    VpiCbHandle::~VpiCbHandle()
    {
        release();
    }

    //
    //
    //

    unsigned GhdlInterface::_interfaceIdCount = 0;

    void* GhdlInterface::_currentCallback = nullptr;

    std::unique_ptr<std::function<void()>> GhdlInterface::_extendedCallbackLifetime = nullptr;

    bool GhdlInterface::_stopped = true;

    void ghdlInterfaceStartup()
    {
        GhdlInterface& interface = GhdlInterface::singleton();
        interface.runStartupFunctions();
    }

    void GhdlInterface::_clearHandle(VpiHandle& handle)
    {
        if (handle.interfaceId() == _interfaceId)
        {
            const int result = _vpiFunctions->free_object(handle.get());

            if (result == 0)
            {
                std::cerr << "WARN: free object failed\n";
            }
        }
    }

    void GhdlInterface::_removeCallback(VpiCbHandle& handle, std::unique_ptr<std::function<void()>>& callback)
    {
        if (handle.interfaceId() == _interfaceId and handle.get() != nullptr)
        {
            if (callback.get() == _currentCallback)
            {
                _extendedCallbackLifetime = std::move(callback);
                _extendedCallbackHandle = handle.get();
                return;
            }

            const int result = _vpiFunctions->remove_cb(handle.get());

            if (result == 0)
            {
                std::cerr << "WARN: remove callback failed\n";
            }
        }
    }

    GhdlInterface::GhdlInterface(std::filesystem::path selfLibPath)
        : _selfLibPath{ selfLibPath }
    {}

    std::string GhdlInterface::_findLibPath()
    {
        static std::mutex mtx;
        std::lock_guard lock{ mtx };

        void* currentExecutable = ::dlopen(NULL, RTLD_LAZY);

        if (currentExecutable == nullptr)
        {
            std::runtime_error(std::string("dlopen failed with error ") + ::dlerror());
        }

        struct link_map* linkMap = nullptr;

        int ret = ::dlinfo(currentExecutable, RTLD_DI_LINKMAP, &linkMap);

        if (ret != 0)
        {
            std::runtime_error(std::string("dlinfo failed with error ") + ::dlerror());
        }

        for (; linkMap != nullptr; linkMap = linkMap->l_next)
        {
            std::string path = linkMap->l_name;

            if (path.find("cohdl_sim_ghdl_interface") != path.npos)
            {
                ::dlclose(currentExecutable);
                return path;
            }
        }

        ::dlclose(currentExecutable);

        throw std::runtime_error("_findLibPath failed");
    }

    VpiCbHandle GhdlInterface::_registerCallback(void* rawData, std::function<void()> callback, bool removeRequired)
    {
        using CallbackType = decltype(callback);

        auto ownedCallback = std::make_unique<CallbackType>(std::move(callback));

        s_cb_data* data = (s_cb_data*) rawData;

        data->user_data = (PLI_BYTE8*) ownedCallback.get();

        data->cb_rtn = [](p_cb_data data) -> PLI_INT32 {
            if (_extendedCallbackLifetime != nullptr)
            {
                if ((void*) _extendedCallbackLifetime.get() == (void*) data->user_data)
                {
                    std::cerr << "callback called after released\n";
                    return 0;
                }

                auto& interface = GhdlInterface::singleton();

                int result = interface._vpiFunctions->remove_cb((vpiHandle) _extendedCallbackHandle);
                _extendedCallbackHandle = nullptr;
                _extendedCallbackLifetime.reset();

                if (result == 0)
                {
                    std::cerr << "REMOVE_CB failed in handler\n";
                }
            }

            try
            {
                auto* fn = (CallbackType*) data->user_data;
                _currentCallback = (void*) fn;

                if (fn == nullptr)
                {
                    std::cerr << "VALUE IS NULLPTR\n";
                }
                else
                {
                    if (not _stopped)
                    {
                        (*fn)();
                    }
                }
            }
            catch(const std::exception& e)
            {
                std::cerr << e.what() << '\n';
                GhdlInterface::singleton().finish_simulation();
            }
            catch(...)
            {
                _currentCallback = nullptr;
                throw;
            }

            _currentCallback = nullptr;
            return 0;
        };

        vpiHandle handle = _vpiFunctions->register_cb(data);

        if (handle == nullptr)
            throw std::runtime_error{ "registering callback failed" };

        return VpiCbHandle{ handle, *this, std::move(ownedCallback), removeRequired };
    }

    GhdlInterface& GhdlInterface::singleton()
    {
        static GhdlInterface singletonObj{ _findLibPath() };
        return singletonObj;
    }

    unsigned GhdlInterface::id()
    {
        return _interfaceId;
    }


    void GhdlInterface::addStartupFunction(std::function<void()> fn)
    {
        _startupFunctions.emplace_back(std::move(fn));
    }

    void GhdlInterface::runStartupFunctions()
    {
        for (auto& fn : _startupFunctions)
        {
            fn();
        }
    }

    void GhdlInterface::clearStartupFunctions()
    {
        _startupFunctions.clear();
    }

    void GhdlInterface::start(std::filesystem::path simulationSo, const std::vector<std::string>& args)
    {
        if (_dlHandle != nullptr)
        {
            throw std::runtime_error("an instance of ghdl is already running");
        }

        _args.clear();
        _args.push_back("wrapped-ghdl-simulation");

        for (const std::string& arg : args)
            _args.emplace_back(arg);

        _args.push_back(std::string("--vpi=")+_selfLibPath.string());
        _argsPtr.clear();

        for (std::string& arg : _args)
            _argsPtr.push_back(arg.data());

        _dlHandle = ::dlopen(simulationSo.c_str(),  RTLD_NOW | RTLD_GLOBAL);

        if (_dlHandle == nullptr)
        {
            throw std::runtime_error("dlopen failed for '" + simulationSo.string() + "' with error " + ::dlerror());
        }

        ++_interfaceIdCount;
        _interfaceId = _interfaceIdCount;

        _vpiFunctions = std::make_unique<VpiFunctions>();

        load_symbol(_dlHandle, "ghdl_main", _vpiFunctions->ghdl_main);
        
        load_symbol(_dlHandle, "vpi_handle_by_name", _vpiFunctions->handle_by_name);
        load_symbol(_dlHandle, "vpi_get_value", _vpiFunctions->get_value);
        load_symbol(_dlHandle, "vpi_put_value", _vpiFunctions->put_value);
        load_symbol(_dlHandle, "vpi_register_cb", _vpiFunctions->register_cb);
        load_symbol(_dlHandle, "vpi_free_object", _vpiFunctions->free_object);
        load_symbol(_dlHandle, "vpi_remove_cb", _vpiFunctions->remove_cb);
        load_symbol(_dlHandle, "vpi_control", _vpiFunctions->control);

        _stopped = false;

        _vpiFunctions->ghdl_main(_argsPtr.size(), _argsPtr.data());
        _stopped = true;
    }

    void GhdlInterface::stop()
    {
        if (_dlHandle != nullptr)
        {
            finish_simulation();
            _interfaceId = -1;
            ::dlclose(_dlHandle);
            _dlHandle = nullptr;
            _stopped = true;
        }
    }

    //
    //

    VpiObjHandle GhdlInterface::handle_by_name(std::string name)
    {
        void* result = _vpiFunctions->handle_by_name((PLI_BYTE8*) name.c_str(),  nullptr);

        if (result == nullptr)
        {
            throw std::runtime_error("invalid handle name: " + name);
        }

        return VpiObjHandle{ result, *this };
    }

    void GhdlInterface::put_value(VpiObjHandle& handle, BitState state)
    {
        // GHDL only implements put_value for integer and bin str value type
        s_vpi_value val;
        val.format = vpiBinStrVal;

        PLI_BYTE8 bin_str[] = {
            decodeBitState(state),
            0
        };

        val.value.str = bin_str;

        _vpiFunctions->put_value(handle.get(), &val, nullptr, vpiNoDelay | vpiPureTransportDelay);
    }

    void GhdlInterface::put_value(VpiObjHandle& handle, const std::string& binStr)
    {
        s_vpi_value val;
        val.format = vpiBinStrVal;

        val.value.str = (PLI_BYTE8*) binStr.c_str();

        _vpiFunctions->put_value(handle.get(), &val, nullptr, vpiNoDelay | vpiPureTransportDelay);
    }

    void GhdlInterface::put_value(VpiObjHandle& handle, int intValue)
    {
        s_vpi_value val;
        val.format = vpiIntVal;
        val.value.integer = intValue;

        _vpiFunctions->put_value(handle.get(), &val, nullptr, vpiNoDelay | vpiPureTransportDelay);
    }

    std::string GhdlInterface::get_binstr(const VpiObjHandle& handle) const
    {
        ::s_vpi_value val;
        val.format = vpiBinStrVal;

        _vpiFunctions->get_value(handle.get(), &val);

        return std::string{ val.value.str };
    }

    VpiCbHandle GhdlInterface::callback_start_of_simulation(std::function<void()> callback)
    {
        s_cb_data data;

        s_vpi_time time{};
        time.type = vpiSimTime;
        s_vpi_value value{};
        value.format = vpiBinStrVal;
        
        data.reason = cbStartOfSimulation;
        data.obj = nullptr;
        data.time = &time;
        data.value = &value;
        data.index = 0;

        return _registerCallback(&data, std::move(callback), false);
    }

    VpiCbHandle GhdlInterface::callback_end_of_simulation(std::function<void()> callback)
    {
        s_cb_data data;

        s_vpi_time time{};
        time.type = vpiSimTime;
        s_vpi_value value{};
        value.format = vpiBinStrVal;
        
        data.reason = cbEndOfSimulation;
        data.obj = nullptr;
        data.time = &time;
        data.value = &value;
        data.index = 0;

        return _registerCallback(&data, std::move(callback), false);
    }

    VpiCbHandle GhdlInterface::callback_delay(unsigned duration, std::function<void()> callback)
    {
        s_cb_data data;
        s_vpi_time time;

        s_vpi_value value{};
        value.format = vpiBinStrVal;

        time.type = vpiSimTime;
        time.high = 0;
        time.low = duration;
        time.real = 0;
        
        data.reason = cbAfterDelay;
        data.obj = nullptr;
        data.time = &time;
        data.value = &value;
        data.index = 0;

        return _registerCallback(&data, std::move(callback), false);
    }

    VpiCbHandle GhdlInterface::callback_next_sim_time(std::function<void()> callback)
    {
        s_cb_data data;

        s_vpi_time time{};
        time.type = vpiSimTime;
        s_vpi_value value{};
        value.format = vpiBinStrVal;
        
        data.reason = cbNextSimTime;
        data.obj = nullptr;
        data.time = &time;
        data.value = &value;
        data.index = 0;

        return _registerCallback(&data, std::move(callback), false);
    }

    VpiCbHandle GhdlInterface::callback_value_change(const VpiObjHandle& handle, std::function<void()> callback)
    {
        s_cb_data data;
        s_vpi_time time{};
        time.type = vpiSimTime;
        s_vpi_value value{};
        value.format = vpiBinStrVal;

        data.reason = cbValueChange;
        data.obj = handle.get();
        data.time = &time;
        data.value = &value;
        data.index = 0;

        return _registerCallback(&data, std::move(callback), true);
    }

    void GhdlInterface::finish_simulation()
    {
        _vpiFunctions->control(vpiFinish, 2);
        _stopped = true;
    }

    GhdlInterface::~GhdlInterface()
    {}
}