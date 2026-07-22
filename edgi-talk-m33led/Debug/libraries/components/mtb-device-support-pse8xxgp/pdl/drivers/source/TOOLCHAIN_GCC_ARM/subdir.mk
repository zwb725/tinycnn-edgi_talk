################################################################################
# 自动生成的文件。不要编辑！
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
S_UPPER_SRCS += \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/TOOLCHAIN_GCC_ARM/cy_syslib_ext.S 

OBJS += \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/TOOLCHAIN_GCC_ARM/cy_syslib_ext.o 

S_UPPER_DEPS += \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/TOOLCHAIN_GCC_ARM/cy_syslib_ext.d 


# Each subdirectory must supply rules for building sources it contributes
libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/TOOLCHAIN_GCC_ARM/%.o: ../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/TOOLCHAIN_GCC_ARM/%.S
	arm-none-eabi-gcc -x assembler-with-cpp -Xassembler -mimplicit-it=thumb -mcpu=cortex-m33 -mthumb -mfpu=fpv5-sp-d16 -mfloat-abi=softfp -ffunction-sections -fdata-sections -ffat-lto-objects -nostartfiles -g -Wall -pipe -O3 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

