#pragma once

#include <array>
#include <vector>
#include <iostream>

#include <functional>
#include <filesystem>
#include <optional>

namespace ghdl_cohdl_interface
{
    void ghdlInterfaceStartup();

    struct VpiFunctions;
    class GhdlInterface;

    enum class BitState
    {
        LOW,
        HIGH,
        HIGH_IMPEDANCE,
        UNDEFINED,
        WEAK_HIGH,
        WEAK_LOW,
        DONT_CARE 
    };

    inline char decodeBitState(BitState state)
    {
        switch (state)
        {
            case BitState::LOW: return '0';
            case BitState::HIGH: return '1';
            case BitState::HIGH_IMPEDANCE: return 'Z';
            case BitState::UNDEFINED: return 'U';
            case BitState::WEAK_HIGH: return 'H';
            case BitState::WEAK_LOW: return 'L';
            case BitState::DONT_CARE: return '-';
        }

        return 'X';
    }

    class AnyPtr
    {
        void* _ptr = nullptr;
    public:

        AnyPtr(void* ptr)
            : _ptr{ ptr }
        {}

        void clear() noexcept
        {
            _ptr = nullptr;
        }

        template<typename T>
        operator T* () const
        {
            return static_cast<T*>(_ptr);
        }

        void* ptr() noexcept
        {
            return _ptr;
        }

        const void* ptr() const noexcept
        {
            return _ptr;
        }

        [[nodiscard]]
        constexpr bool operator== (std::nullptr_t) const noexcept
        {
            return _ptr == nullptr;
        }

        [[nodiscard]]
        constexpr bool operator!= (std::nullptr_t) const noexcept
        {
            return _ptr != nullptr;
        }

        std::uintptr_t id() const noexcept
        {
            return reinterpret_cast<std::uint64_t>(_ptr);
        }
    };

    class VpiHandle
    {
    protected:
        AnyPtr _handle;
        GhdlInterface& _interface;
        unsigned _interfaceId;
    public:

        VpiHandle(void* handle, GhdlInterface& interface);

        VpiHandle(const VpiHandle&) = delete;

        VpiHandle(VpiHandle&& other);

        AnyPtr get() const noexcept;

        unsigned interfaceId() const noexcept;

        std::uintptr_t id() const noexcept;

        virtual ~VpiHandle();
    };

    class VpiObjHandle : public VpiHandle
    {
    public:
        using VpiHandle::VpiHandle;

        void put_value(BitState state);

        void put_value(const std::string& binstr);

        void put_value(int intValue);

        std::string get_binstr() const;
    };

    class VpiCbHandle final : public VpiHandle
    {
        friend GhdlInterface;

        std::unique_ptr<std::function<void()>> _callback;
        bool _removeRequired;

        VpiCbHandle(void* handle, GhdlInterface& interface, std::unique_ptr<std::function<void()>> callback, bool removeRequired)
            : VpiHandle{ handle, interface }
            , _callback{ std::move(callback) }
            , _removeRequired{ removeRequired }
        {}

    public:

        VpiCbHandle(const VpiCbHandle&) = delete;

        VpiCbHandle(VpiCbHandle&& other) = default;

        VpiCbHandle& operator= (const VpiCbHandle&) = delete;

        VpiCbHandle& operator= (VpiCbHandle&&) = delete;

        void release();

        ~VpiCbHandle();
    };
    
    class GhdlInterface
    {
        friend VpiHandle;
        friend VpiCbHandle;
        
        static unsigned _interfaceIdCount;
        static void* _currentCallback;

        // TODO: cleanup
        static std::unique_ptr<std::function<void()>> _extendedCallbackLifetime;
        inline static void* _extendedCallbackHandle = nullptr;

        // TODO: find out, why handers are called after simulation is finished
        static bool _stopped;

        unsigned _interfaceId;

        std::vector<std::function<void()>> _startupFunctions;

        std::vector<std::string> _args;
        std::vector<char*> _argsPtr;

        void* _dlHandle = nullptr;

        std::filesystem::path _selfLibPath;

        std::unique_ptr<VpiFunctions> _vpiFunctions;

        GhdlInterface(std::filesystem::path selfLibPath);

        static std::string _findLibPath();

        void _clearHandle(VpiHandle& handle);

        VpiCbHandle _registerCallback(void* cbData, std::function<void()> callback, bool removeRequired);

        void _removeCallback(VpiCbHandle& handle, std::unique_ptr<std::function<void()>>& callback);

    public:

        static GhdlInterface& singleton();

        unsigned id();

        void addStartupFunction(std::function<void()> fn);

        void runStartupFunctions();

        void clearStartupFunctions();

        void start(std::filesystem::path simulationSo, const std::vector<std::string>& args);

        void stop();

        //
        // simulation functions
        //

        VpiObjHandle handle_by_name(std::string name);

        void put_value(VpiObjHandle& handle, BitState state);

        void put_value(VpiObjHandle& handle, const std::string& binStr);

        void put_value(VpiObjHandle& handle, int intValue);

        std::string get_binstr(const VpiObjHandle& handle) const;

        VpiCbHandle callback_start_of_simulation(std::function<void()>);

        VpiCbHandle callback_end_of_simulation(std::function<void()>);

        VpiCbHandle callback_delay(unsigned duration, std::function<void()>);

        VpiCbHandle callback_next_sim_time(std::function<void()>);
        // VpiCbHandle callback_read_only_sync(unsigned duration, void(*)(void*));
        // VpiCbHandle callback_write_only_sync(unsigned duration, void(*)(void*));

        VpiCbHandle callback_value_change(const VpiObjHandle& handle, std::function<void()>);

        void finish_simulation();
    
        ~GhdlInterface();
    };
}