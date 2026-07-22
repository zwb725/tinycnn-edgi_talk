################################################################################
# 自动生成的文件。不要编辑！
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_axidmac.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_dma.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_gpio.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_drv.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_pipe.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_sema.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_scb_common.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_scb_uart.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_sysclk_v2.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_sysint_v2.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syslib.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_pdcm.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_ppu.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_v4.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_systick_v2.c \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/ppu_v1.c 

O_SRCS += \
../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_rtc.o 

OBJS += \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_axidmac.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_dma.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_gpio.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_drv.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_pipe.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_sema.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_scb_common.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_scb_uart.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_sysclk_v2.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_sysint_v2.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syslib.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_pdcm.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_ppu.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_v4.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_systick_v2.o \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/ppu_v1.o 

C_DEPS += \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_axidmac.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_dma.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_gpio.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_drv.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_pipe.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_ipc_sema.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_scb_common.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_scb_uart.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_sysclk_v2.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_sysint_v2.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syslib.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_pdcm.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_ppu.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_syspm_v4.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/cy_systick_v2.d \
./libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/ppu_v1.d 


# Each subdirectory must supply rules for building sources it contributes
libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/%.o: ../libraries/components/mtb-device-support-pse8xxgp/pdl/drivers/source/%.c
	arm-none-eabi-gcc -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\applications" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\board" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\Common\board\ports\display_panels" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\Common\board" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\HAL_Drivers" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\ASRC\COMPONENT_CM33\inc" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\Infineon_cmsis-latest\Core\Include\m-profile" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\Infineon_cmsis-latest\Core\Include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\Infineon_core-lib-latest\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\Infineon_retarget-io-latest" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\async-transfer\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\device-utils\syspm\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\hal\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\pdl\devices\include\ip" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\pdl\devices\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\pdl\drivers\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\pdl\drivers\third_party\COMPONENT_GFXSS\vsi\dcnano8000" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\pdl\drivers\third_party\COMPONENT_GFXSS\vsi\gcnano" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\pdl\drivers\third_party\COMPONENT_GFXSS" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-device-support-pse8xxgp\pdl\drivers\third_party\ethernet\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-ipc\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-srf\include\COMPONENT_NON_SECURE_DEVICE\COMPONENT_MW_MTB_IPC" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-srf\include\COMPONENT_NON_SECURE_DEVICE" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libraries\components\mtb-srf\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libs\TARGET_APP_KIT_PSE84_EVAL_EPC2\bluetooth" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libs\TARGET_APP_KIT_PSE84_EVAL_EPC2\config\GeneratedSource" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libs\TARGET_APP_KIT_PSE84_EVAL_EPC2\config" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\libs\TARGET_APP_KIT_PSE84_EVAL_EPC2" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\components\drivers\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\components\finsh" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\components\libc\compilers\common\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\components\libc\compilers\newlib" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\components\libc\posix\io\epoll" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\components\libc\posix\io\eventfd" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\components\libc\posix\io\poll" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\components\libc\posix\ipc" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\include" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\libcpu\arm\common" -I"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rt-thread\libcpu\arm\cortex-m33" -include"C:\RT-ThreadStudio\workspace\edgi-talk-m33led\rtconfig_preinc.h" -std=gnu11 -mcpu=cortex-m33 -mthumb -mfpu=fpv5-sp-d16 -mfloat-abi=softfp -ffunction-sections -fdata-sections -ffat-lto-objects -nostartfiles -g -Wall -pipe -O3 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

