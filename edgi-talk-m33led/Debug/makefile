################################################################################
# 自动生成的文件。不要编辑！
################################################################################

-include ../makefile.init

RM := rm -rf

# All of the sources participating in the build are defined here
-include sources.mk
-include rt-thread/src/subdir.mk
-include rt-thread/libcpu/arm/cortex-m33/subdir.mk
-include rt-thread/libcpu/arm/common/subdir.mk
-include rt-thread/components/libc/compilers/newlib/subdir.mk
-include rt-thread/components/libc/compilers/common/subdir.mk
-include rt-thread/components/finsh/subdir.mk
-include rt-thread/components/drivers/serial/subdir.mk
-include rt-thread/components/drivers/misc/subdir.mk
-include rt-thread/components/drivers/ipc/subdir.mk
-include rt-thread/components/drivers/core/subdir.mk
-include libs/TARGET_APP_KIT_PSE84_EVAL_EPC2/config/GeneratedSource/subdir.mk
-include libs/TARGET_APP_KIT_PSE84_EVAL_EPC2/COMPONENT_CM33/COMPONENT_NON_SECURE_DEVICE/subdir.mk
-include libs/TARGET_APP_KIT_PSE84_EVAL_EPC2/subdir.mk
-include libraries/components/mtb-srf/subdir.mk
-include libraries/components/mtb-ipc/source/subdir.mk
-include libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/TOOLCHAIN_GCC_ARM/subdir.mk
-include libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/subdir.mk
-include libraries/components/mtb-device-support-pse8xxgp/pdl/devices/source/subdir.mk
-include libraries/components/mtb-device-support-pse8xxgp/hal/source/subdir.mk
-include libraries/components/mtb-device-support-pse8xxgp/device-utils/syspm/source/subdir.mk
-include libraries/components/async-transfer/source/subdir.mk
-include libraries/components/Infineon_retarget-io-latest/subdir.mk
-include libraries/HAL_Drivers/subdir.mk
-include board/subdir.mk
-include applications/subdir.mk
-include subdir.mk
-include objects.mk

ifneq ($(MAKECMDGOALS),clean)
ifneq ($(strip $(CC_DEPS)),)
-include $(CC_DEPS)
endif
ifneq ($(strip $(C++_DEPS)),)
-include $(C++_DEPS)
endif
ifneq ($(strip $(C_UPPER_DEPS)),)
-include $(C_UPPER_DEPS)
endif
ifneq ($(strip $(CXX_DEPS)),)
-include $(CXX_DEPS)
endif
ifneq ($(strip $(ASM_DEPS)),)
-include $(ASM_DEPS)
endif
ifneq ($(strip $(S_DEPS)),)
-include $(S_DEPS)
endif
ifneq ($(strip $(S_UPPER_DEPS)),)
-include $(S_UPPER_DEPS)
endif
ifneq ($(strip $(C_DEPS)),)
-include $(C_DEPS)
endif
ifneq ($(strip $(CPP_DEPS)),)
-include $(CPP_DEPS)
endif
endif

-include ../makefile.defs

# Add inputs and outputs from these tool invocations to the build variables 
SECONDARY_FLASH += \
rtthread.hex \

SECONDARY_SIZE += \
rtthread.siz \


# 所有目标
all: rtthread.elf secondary-outputs

# 工具调用
rtthread.elf: $(OBJS) $(USER_OBJS)
	arm-none-eabi-g++ -T "C:\RT-ThreadStudio\workspace\edgi-talk-m33led\board\linker_scripts\link.ld" -nostartfiles -Xlinker --gc-sections -Wl,-Map,"rtthread.map" -Xlinker --cref -mcpu=cortex-m33 -mthumb -mfpu=fpv5-sp-d16 -mfloat-abi=softfp -ffunction-sections -fdata-sections -ffat-lto-objects -nostartfiles -g -Wall -pipe -O3 -o "rtthread.elf" $(OBJS) $(USER_OBJS) $(LIBS)

rtthread.hex: rtthread.elf
	arm-none-eabi-objcopy -O ihex "rtthread.elf"  "rtthread.hex"
	$(MAKE) --no-print-directory post-build

rtthread.siz: rtthread.elf
	arm-none-eabi-size --format=berkeley "rtthread.elf"

# 其他目标
clean:
	-$(RM) $(CC_DEPS)$(C++_DEPS)$(OBJS)$(C_UPPER_DEPS)$(CXX_DEPS)$(SECONDARY_FLASH)$(SECONDARY_SIZE)$(ASM_DEPS)$(S_DEPS)$(S_UPPER_DEPS)$(C_DEPS)$(CPP_DEPS) rtthread.elf
	-@echo ' '

post-build:
	-arm-none-eabi-objcopy -O ihex "rtthread.elf" "rtthread.hex";../tools/edgeprotecttools/bin/edgeprotecttools.exe run-config -i ../config/boot_with_extended_boot.json
	-@echo ' '

secondary-outputs: $(SECONDARY_FLASH) $(SECONDARY_SIZE)

.PHONY: all clean dependents post-build

-include ../makefile.targets
