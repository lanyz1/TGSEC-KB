# ============================================================
# PHOENIX-FORGE · 矿工配置模板（部署时替换 <...> 占位符）
# 币种：Pearl (PRL) · 矿工：PeakMiner 系（环境变量驱动）
# 池：Kryptex（8 区域 fallback，SSL 优先）
# 换币/换池：改 PEAK_COIN / PEAK_POOL 即可
# ============================================================
export PEAK_COIN=pearl
export PEAK_WALLET=<WALLET>/<WORKER>
export PEAK_LOG_FILE=<MINER_DIR>/logs/log.log
export PEAK_LOG_APPEND=true
export CUDA_VISIBLE_DEVICES=<GPUS>
export PEAK_API_PORT=0
export PEAK_DNS_OVER_HTTPS=on
export PEAK_POOL=stratum+ssl://prl.kryptex.network:8048,stratum+ssl://prl-eu.kryptex.network:8048,stratum+ssl://prl-ru.kryptex.network:8048,stratum+ssl://prl-us.kryptex.network:8048,stratum+ssl://prl-sg.kryptex.network:8048,stratum+ssl://prl-br.kryptex.network:8048,stratum+ssl://prl-ae.kryptex.network:8048,stratum+tcp://prl.kryptex.network:7048,stratum+tcp://prl-eu.kryptex.network:7048,stratum+tcp://prl-us.kryptex.network:7048,stratum+tcp://prl-sg.kryptex.network:7048
