## 2. EVM链 & Solana链智能合约开发

### 2.1 EVM智能合约开发

#### 2.1.1 代币合约

**标准ERC-20代币（含高级功能）**：

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title 自定义ERC-20代币 — 含销毁/投票/黑名单/交易限制/反巨鲸
/// @custom:security-contact <EMAIL-REDACTED>
contract CustomToken is ERC20, ERC20Burnable, ERC20Permit, Ownable, ReentrancyGuard {
    // === 状态变量 ===
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 10亿
    uint256 public maxTxAmount;               // 单笔最大交易量
    uint256 public maxWalletAmount;           // 单钱包最大持仓
    bool public tradingEnabled;               // 交易开关
    bool public limitsEnabled = true;         // 限制开关
    
    mapping(address => bool) public isBlacklisted;
    mapping(address => bool) public isExcludedFromLimits;
    
    // === 事件 ===
    event TradingEnabled(uint256 timestamp);
    event BlacklistUpdated(address indexed account, bool status);
    event LimitsUpdated(uint256 maxTx, uint256 maxWallet);
    
    // === 手续费机制（可扩展） ===
    uint256 public buyFee = 0;   // 0.5% = 50
    uint256 public sellFee = 0;
    uint256 public feeDenominator = 10000;
    address public feeReceiver;
    mapping(address => bool) public isExcludedFromFees;
    
    constructor(
        string memory name,
        string memory symbol,
        address initialOwner,
        address _feeReceiver
    ) ERC20(name, symbol) ERC20Permit(name) Ownable(initialOwner) {
        feeReceiver = _feeReceiver;
        maxTxAmount = MAX_SUPPLY;
        maxWalletAmount = MAX_SUPPLY;
        
        // 预分配排除限制
        isExcludedFromLimits[initialOwner] = true;
        isExcludedFromLimits[address(this)] = true;
        isExcludedFromLimits[address(0)] = true;
        isExcludedFromFees[initialOwner] = true;
        isExcludedFromFees[address(this)] = true;
    }
    
    // === 转账钩子 ===
    function _update(address from, address to, uint256 value) internal virtual override {
        // 黑名单检查
        require(!isBlacklisted[from] && !isBlacklisted[to], "Blacklisted");
        
        if (from != address(0) && to != address(0)) {
            // 交易限制检查
            if (limitsEnabled && !isExcludedFromLimits[from] && !isExcludedFromLimits[to]) {
                require(tradingEnabled, "Trading disabled");
                require(value <= maxTxAmount, "Exceeds max tx");
                if (to != address(0)) {
                    require(balanceOf(to) + value <= maxWalletAmount, "Exceeds max wallet");
                }
            }
            
            // 手续费处理
            uint256 fee = 0;
            bool isBuy = _isBuy(from);
            bool isSell = _isSell(to);
            
            if (!isExcludedFromFees[from] && !isExcludedFromFees[to]) {
                if (isBuy && buyFee > 0) {
                    fee = (value * buyFee) / feeDenominator;
                } else if (isSell && sellFee > 0) {
                    fee = (value * sellFee) / feeDenominator;
                }
            }
            
            if (fee > 0) {
                super._update(from, feeReceiver, fee);
                value -= fee;
            }
        }
        super._update(from, to, value);
    }
    
    function _isBuy(address from) internal view returns (bool) {
        // 从LP买入逻辑：判断from是否为DEX pair地址
        return from != address(0) && !isExcludedFromFees[from];
    }
    
    function _isSell(address to) internal view returns (bool) {
        return to != address(0) && !isExcludedFromFees[to];
    }
    
    // === 管理函数 ===
    function enableTrading() external onlyOwner {
        tradingEnabled = true;
        emit TradingEnabled(block.timestamp);
    }
    
    function setBlacklist(address account, bool status) external onlyOwner {
        isBlacklisted[account] = status;
        emit BlacklistUpdated(account, status);
    }
    
    function setLimits(uint256 _maxTx, uint256 _maxWallet) external onlyOwner {
        maxTxAmount = _maxTx;
        maxWalletAmount = _maxWallet;
        emit LimitsUpdated(_maxTx, _maxWallet);
    }
    
    function setFees(uint256 _buyFee, uint256 _sellFee) external onlyOwner {
        require(_buyFee <= 1000 && _sellFee <= 1000, "Fee too high"); // 最大10%
        buyFee = _buyFee;
        sellFee = _sellFee;
    }
}
```

**ERC-721 NFT合约（含白名单/预售/版税）**：

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Royalty.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title NFT Collection — 白名单Merkle Tree + 预售 + 版税 + 盲盒揭示
contract NFTCollection is ERC721, ERC721Enumerable, ERC721Royalty, Ownable, ReentrancyGuard {
    using Strings for uint256;
    
    uint256 public constant MAX_SUPPLY = 10000;
    uint256 public constant MAX_PER_WALLET = 10;
    uint256 public constant WHITELIST_PRICE = 0.05 ether;
    uint256 public constant PUBLIC_PRICE = 0.08 ether;
    
    bytes32 public merkleRoot;
    string public baseURI;
    string public unrevealedURI;
    bool public revealed;
    bool public whitelistMintOpen;
    bool public publicMintOpen;
    
    mapping(address => uint256) public whitelistMinted;
    mapping(address => uint256) public publicMinted;
    
    event Minted(address indexed to, uint256 tokenId, bool isWhitelist);
    event Revealed(string baseURI);
    
    constructor(
        string memory _name,
        string memory _symbol,
        string memory _unrevealedURI,
        address royaltyReceiver,
        uint96 royaltyFeeNumerator  // 如 500 = 5%
    ) ERC721(_name, _symbol) Ownable(msg.sender) {
        unrevealedURI = _unrevealedURI;
        _setDefaultRoyalty(royaltyReceiver, royaltyFeeNumerator);
    }
    
    // === 白名单铸造 ===
    function whitelistMint(bytes32[] calldata proof, uint256 quantity) 
        external payable nonReentrant {
        require(whitelistMintOpen, "Whitelist mint closed");
        require(totalSupply() + quantity <= MAX_SUPPLY, "Sold out");
        require(msg.value >= WHITELIST_PRICE * quantity, "Insufficient ETH");
        require(whitelistMinted[msg.sender] + quantity <= MAX_PER_WALLET, "Exceeds limit");
        
        bytes32 leaf = keccak256(abi.encodePacked(msg.sender));
        require(MerkleProof.verify(proof, merkleRoot, leaf), "Invalid proof");
        
        whitelistMinted[msg.sender] += quantity;
        _batchMint(msg.sender, quantity);
        emit Minted(msg.sender, totalSupply(), true);
    }
    
    // === 公开铸造 ===
    function publicMint(uint256 quantity) external payable nonReentrant {
        require(publicMintOpen, "Public mint closed");
        require(totalSupply() + quantity <= MAX_SUPPLY, "Sold out");
        require(msg.value >= PUBLIC_PRICE * quantity, "Insufficient ETH");
        require(publicMinted[msg.sender] + quantity <= MAX_PER_WALLET, "Exceeds limit");
        
        publicMinted[msg.sender] += quantity;
        _batchMint(msg.sender, quantity);
        emit Minted(msg.sender, totalSupply(), false);
    }
    
    // === 批量铸造 ===
    function _batchMint(address to, uint256 quantity) internal {
        uint256 currentId = totalSupply();
        for (uint256 i = 0; i < quantity; i++) {
            _safeMint(to, currentId + i + 1);
        }
    }
    
    // === 揭示 ===
    function reveal(string calldata _baseURI) external onlyOwner {
        revealed = true;
        baseURI = _baseURI;
        emit Revealed(_baseURI);
    }
    
    // === Token URI ===
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        if (!revealed) return unrevealedURI;
        return string(abi.encodePacked(baseURI, tokenId.toString(), ".json"));
    }
    
    // === 管理函数 ===
    function setMerkleRoot(bytes32 _root) external onlyOwner { merkleRoot = _root; }
    function toggleWhitelistMint() external onlyOwner { whitelistMintOpen = !whitelistMintOpen; }
    function togglePublicMint() external onlyOwner { publicMintOpen = !publicMintOpen; }
    function withdraw() external onlyOwner {
        (bool success, ) = msg.sender.call{value: address(this).balance}("");
        require(success, "Transfer failed");
    }
    
    // === 必需覆写 ===
    function _update(address to, uint256 tokenId, address auth) 
        internal override(ERC721, ERC721Enumerable) returns (address) {
        return super._update(to, tokenId, auth);
    }
    
    function _increaseBalance(address account, uint128 value) 
        internal override(ERC721, ERC721Enumerable) {
        super._increaseBalance(account, value);
    }
    
    function supportsInterface(bytes4 interfaceId) 
        public view override(ERC721, ERC721Enumerable, ERC721Royalty) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}
```

#### 2.1.2 DeFi合约开发

**UniswapV3风格AMM（简化版）**：

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title 简化AMM（恒定乘积 x*y=k）
contract SimpleAMM {
    using SafeERC20 for IERC20;
    
    IERC20 public immutable token0;
    IERC20 public immutable token1;
    uint256 public reserve0;
    uint256 public reserve1;
    uint256 public totalLiquidity;
    
    mapping(address => uint256) public liquidityOf;
    mapping(address => mapping(address => uint256)) public allowances;
    
    event Mint(address indexed sender, uint256 amount0, uint256 amount1, uint256 liquidity);
    event Burn(address indexed sender, uint256 amount0, uint256 amount1, uint256 liquidity);
    event Swap(address indexed sender, uint256 amountIn, uint256 amountOut, bool isToken0);
    
    constructor(address _token0, address _token1) {
        token0 = IERC20(_token0);
        token1 = IERC20(_token1);
    }
    
    /// @notice 添加流动性
    function addLiquidity(uint256 amount0Desired, uint256 amount1Desired) 
        external returns (uint256 liquidity) {
        // 计算最优数量
        (uint256 amount0, uint256 amount1) = _calculateOptimalAmounts(amount0Desired, amount1Desired);
        
        token0.safeTransferFrom(msg.sender, address(this), amount0);
        token1.safeTransferFrom(msg.sender, address(this), amount1);
        
        if (totalLiquidity == 0) {
            liquidity = Math.sqrt(amount0 * amount1) - 1000; // 锁定最小流动性
        } else {
            uint256 liquidity0 = (amount0 * totalLiquidity) / reserve0;
            uint256 liquidity1 = (amount1 * totalLiquidity) / reserve1;
            liquidity = liquidity0 < liquidity1 ? liquidity0 : liquidity1;
        }
        
        require(liquidity > 0, "INSUFFICIENT_LIQUIDITY");
        liquidityOf[msg.sender] += liquidity;
        totalLiquidity += liquidity;
        reserve0 += amount0;
        reserve1 += amount1;
        
        emit Mint(msg.sender, amount0, amount1, liquidity);
    }
    
    /// @notice 移除流动性
    function removeLiquidity(uint256 liquidity) 
        external returns (uint256 amount0, uint256 amount1) {
        require(liquidityOf[msg.sender] >= liquidity, "INSUFFICIENT_LIQUIDITY");
        
        amount0 = (liquidity * reserve0) / totalLiquidity;
        amount1 = (liquidity * reserve1) / totalLiquidity;
        
        liquidityOf[msg.sender] -= liquidity;
        totalLiquidity -= liquidity;
        reserve0 -= amount0;
        reserve1 -= amount1;
        
        token0.safeTransfer(msg.sender, amount0);
        token1.safeTransfer(msg.sender, amount1);
        
        emit Burn(msg.sender, amount0, amount1, liquidity);
    }
    
    /// @notice 兑换（token0→token1 或 token1→token0）
    function swap(uint256 amountIn, bool isToken0, uint256 minAmountOut) 
        external returns (uint256 amountOut) {
        (uint256 reserveIn, uint256 reserveOut) = isToken0 
            ? (reserve0, reserve1) : (reserve1, reserve0);
        
        // 恒定乘积：x*y=k => (x+dx)*(y-dy)=k => dy = y*dx/(x+dx)
        uint256 amountInWithFee = amountIn * 997; // 0.3% fee
        amountOut = (reserveOut * amountInWithFee) / (reserve0 * 1000 + amountInWithFee);
        require(amountOut >= minAmountOut, "SLIPPAGE");
        
        if (isToken0) {
            token0.safeTransferFrom(msg.sender, address(this), amountIn);
            reserve0 += amountIn;
            reserve1 -= amountOut;
            token1.safeTransfer(msg.sender, amountOut);
        } else {
            token1.safeTransferFrom(msg.sender, address(this), amountIn);
            reserve1 += amountIn;
            reserve0 -= amountOut;
            token0.safeTransfer(msg.sender, amountOut);
        }
        
        emit Swap(msg.sender, amountIn, amountOut, isToken0);
        require(reserve0 * reserve1 >= 0, "K");
    }
    
    function _calculateOptimalAmounts(uint256 amount0Desired, uint256 amount1Desired)
        internal view returns (uint256 amount0, uint256 amount1) {
        if (reserve0 == 0 && reserve1 == 0) {
            return (amount0Desired, amount1Desired);
        }
        uint256 amount1Optimal = (amount0Desired * reserve1) / reserve0;
        if (amount1Optimal <= amount1Desired) {
            return (amount0Desired, amount1Optimal);
        }
        uint256 amount0Optimal = (amount1Desired * reserve0) / reserve1;
        return (amount0Optimal, amount1Desired);
    }
}
```

**质押挖矿合约（Staking）**：

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Staking Pool — 质押ERC-20获得奖励代币
contract StakingPool is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    
    IERC20 public stakingToken;    // 质押代币
    IERC20 public rewardToken;     // 奖励代币
    
    uint256 public rewardRate;           // 每秒每个质押代币的奖励
    uint256 public totalStaked;
    uint256 public lastUpdateTime;
    uint256 public rewardPerTokenStored;
    uint256 public lockPeriod = 7 days;  // 锁仓期
    uint256 public earlyUnstakeFee = 500; // 5%提前提取手续费
    
    struct StakeInfo {
        uint256 amount;
        uint256 rewardPerTokenPaid;
        uint256 rewards;
        uint256 stakedAt;
    }
    mapping(address => StakeInfo) public stakes;
    
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
    event RewardPaid(address indexed user, uint256 reward);
    
    constructor(address _stakingToken, address _rewardToken, uint256 _rewardRate) 
        Ownable(msg.sender) {
        stakingToken = IERC20(_stakingToken);
        rewardToken = IERC20(_rewardToken);
        rewardRate = _rewardRate;
    }
    
    modifier updateReward(address account) {
        rewardPerTokenStored = rewardPerToken();
        lastUpdateTime = block.timestamp;
        if (account != address(0)) {
            stakes[account].rewards = earned(account);
            stakes[account].rewardPerTokenPaid = rewardPerTokenStored;
        }
        _;
    }
    
    function rewardPerToken() public view returns (uint256) {
        if (totalStaked == 0) return rewardPerTokenStored;
        return rewardPerTokenStored + 
            (rewardRate * (block.timestamp - lastUpdateTime) * 1e18) / totalStaked;
    }
    
    function earned(address account) public view returns (uint256) {
        return (stakes[account].amount * 
            (rewardPerToken() - stakes[account].rewardPerTokenPaid)) / 1e18 
            + stakes[account].rewards;
    }
    
    function stake(uint256 amount) external nonReentrant updateReward(msg.sender) {
        require(amount > 0, "Amount = 0");
        stakes[msg.sender].amount += amount;
        stakes[msg.sender].stakedAt = block.timestamp;
        totalStaked += amount;
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        emit Staked(msg.sender, amount);
    }
    
    function unstake(uint256 amount) external nonReentrant updateReward(msg.sender) {
        require(amount > 0 && stakes[msg.sender].amount >= amount, "Invalid amount");
        
        uint256 fee = 0;
        if (block.timestamp < stakes[msg.sender].stakedAt + lockPeriod) {
            fee = (amount * earlyUnstakeFee) / 10000;
        }
        
        stakes[msg.sender].amount -= amount;
        totalStaked -= amount;
        stakingToken.safeTransfer(msg.sender, amount - fee);
        if (fee > 0) stakingToken.safeTransfer(owner(), fee); // 手续费归项目方
        
        emit Unstaked(msg.sender, amount, fee);
    }
    
    function claimReward() external nonReentrant updateReward(msg.sender) {
        uint256 reward = stakes[msg.sender].rewards;
        require(reward > 0, "No reward");
        stakes[msg.sender].rewards = 0;
        rewardToken.safeTransfer(msg.sender, reward);
        emit RewardPaid(msg.sender, reward);
    }
    
    function setRewardRate(uint256 _rate) external onlyOwner updateReward(address(0)) {
        rewardRate = _rate;
    }
    
    function setLockPeriod(uint256 _period) external onlyOwner {
        lockPeriod = _period;
    }
}
```

#### 2.1.3 ERC-4337账户抽象（Account Abstraction）

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/// @title 简单账户抽象钱包 — 支持社交恢复/多签/无Gas交易
contract SimpleAccount {
    using ECDSA for bytes32;
    
    address public owner;
    address[] public guardians;
    uint256 public guardianThreshold;
    uint256 public recoveryDelay = 7 days;
    
    struct RecoveryRequest {
        address newOwner;
        uint256 requestTime;
        uint256 approvals;
    }
    RecoveryRequest public pendingRecovery;
    mapping(address => bool) public hasApproved;
    
    event Executed(address indexed to, uint256 value, bytes data);
    event RecoveryRequested(address indexed newOwner, uint256 requestTime);
    event RecoveryExecuted(address indexed newOwner);
    
    constructor(address _owner, address[] memory _guardians, uint256 _threshold) {
        owner = _owner;
        guardians = _guardians;
        guardianThreshold = _threshold;
    }
    
    /// @notice 验证UserOperation签名（ERC-4337入口点调用）
    function validateUserOp(
        UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 missingAccountFunds
    ) external returns (uint256 validationData) {
        // 验证签名
        bytes32 hash = MessageHashUtils.toEthSignedMessageHash(userOpHash);
        address signer = hash.recover(userOp.signature);
        require(signer == owner, "Invalid signature");
        
        // 支付缺失的Gas
        if (missingAccountFunds > 0) {
            (bool success, ) = payable(msg.sender).call{value: missingAccountFunds}("");
            require(success, "Payment failed");
        }
        
        return 0; // SIG_VALIDATION_SUCCESS
    }
    
    /// @notice 执行任意操作
    function execute(address to, uint256 value, bytes calldata data) 
        external returns (bytes memory result) {
        require(msg.sender == owner || msg.sender == address(this), "Unauthorized");
        (bool success, bytes memory returnData) = to.call{value: value}(data);
        require(success, "Execution failed");
        emit Executed(to, value, data);
        return returnData;
    }
    
    /// @notice 社交恢复：请求更换Owner
    function requestRecovery(address newOwner) external {
        require(_isGuardian(msg.sender), "Not guardian");
        if (pendingRecovery.newOwner != newOwner) {
            pendingRecovery = RecoveryRequest(newOwner, block.timestamp, 0);
            emit RecoveryRequested(newOwner, block.timestamp);
        }
        require(!hasApproved[msg.sender], "Already approved");
        hasApproved[msg.sender] = true;
        pendingRecovery.approvals++;
        
        if (pendingRecovery.approvals >= guardianThreshold) {
            require(block.timestamp >= pendingRecovery.requestTime + recoveryDelay, 
                "Recovery delay");
            owner = pendingRecovery.newOwner;
            delete pendingRecovery;
            emit RecoveryExecuted(newOwner);
        }
    }
    
    function _isGuardian(address account) internal view returns (bool) {
        for (uint256 i = 0; i < guardians.length; i++) {
            if (guardians[i] == account) return true;
        }
        return false;
    }
    
    receive() external payable {}
}
```

### 2.2 Solana智能合约开发

#### 2.2.1 Anchor Program结构

```rust
use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer, MintTo};

declare_id!("Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS");

#[program]
pub mod custom_token {
    use super::*;

    /// 初始化代币Mint和元数据
    pub fn initialize_token(
        ctx: Context<InitializeToken>,
        name: String,
        symbol: String,
        uri: String,
        decimals: u8,
        initial_supply: u64,
    ) -> Result<()> {
        let token_data = &mut ctx.accounts.token_data;
        token_data.authority = ctx.accounts.authority.key();
        token_data.name = name;
        token_data.symbol = symbol;
        token_data.uri = uri;
        token_data.total_supply = 0;
        token_data.bump = ctx.bumps.token_data;

        // 铸造初始供应量
        let cpi_ctx = CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            MintTo {
                mint: ctx.accounts.mint.to_account_info(),
                to: ctx.accounts.token_account.to_account_info(),
                authority: ctx.accounts.authority.to_account_info(),
            },
        );
        token:<REDACTED>, initial_supply)?;

        token_data.total_supply = initial_supply;
        Ok(())
    }

    /// 转账（带自定义逻辑）
    pub fn transfer_with_fee(
        ctx: Context<TransferWithFee>,
        amount: u64,
        fee_bps: u16, // 基点，如 100 = 1%
    ) -> Result<()> {
        require!(fee_bps <= 1000, ErrorCode::FeeTooHigh); // 最大10%

        let fee_amount = (amount as u128 * fee_bps as u128 / 10000) as u64;
        let transfer_amount = amount - fee_amount;

        // 转手续费
        if fee_amount > 0 {
            let cpi_ctx = CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.from.to_account_info(),
                    to: ctx.accounts.fee_vault.to_account_info(),
                    authority: ctx.accounts.authority.to_account_info(),
                },
            );
            token:<REDACTED>, fee_amount)?;
        }

        // 转剩余
        let cpi_ctx = CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.from.to_account_info(),
                to: ctx.accounts.to.to_account_info(),
                authority: ctx.accounts.authority.to_account_info(),
            },
        );
        token:<REDACTED>, transfer_amount)?;

        emit!(TransferEvent {
            from: ctx.accounts.authority.key(),
            to: ctx.accounts.to.key(),
            amount: transfer_amount,
            fee: fee_amount,
        });

        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(name: String, symbol: String, uri: String, decimals: u8, initial_supply: u64)]
pub struct InitializeToken<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,

    /// Mint账户（PDA）
    #[account(
        init,
        payer = authority,
        mint::decimals = decimals,
        mint::authority = authority.key(),
    )]
    pub mint: Account<'info, Mint>,

    /// 代币元数据存储
    #[account(
        init,
        payer = authority,
        space = 8 + TokenData::LEN,
        seeds = [b"token_data", mint.key().as_ref()],
        bump,
    )]
    pub token_data: Account<'info, TokenData>,

    /// 接收初始供应的代币账户
    #[account(
        init,
        payer = authority,
        token::mint = mint,
        token:<REDACTED> = authority,
    )]
    pub token_account: Account<'info, TokenAccount>,

    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct TransferWithFee<'info> {
    pub authority: Signer<'info>,
    #[account(mut)]
    pub from: Account<'info, TokenAccount>,
    #[account(mut)]
    pub to: Account<'info, TokenAccount>,
    #[account(mut)]
    pub fee_vault: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[account]
pub struct TokenData {
    pub authority: Pubkey,       // 32
    pub name: String,            // 4 + len
    pub symbol: String,          // 4 + len
    pub uri: String,             // 4 + len
    pub total_supply: u64,       // 8
    pub bump: u8,                // 1
}

impl TokenData {
    pub const LEN: usize = 32 + (4 + 64) + (4 + 16) + (4 + 200) + 8 + 1 + 64;
}

#[event]
pub struct TransferEvent {
    pub from: Pubkey,
    pub to: Pubkey,
    pub amount: u64,
    pub fee: u64,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Fee cannot exceed 10%")]
    FeeTooHigh,
}
```

#### 2.2.2 Solana DEX集成（Raydium/Jupiter）

```rust
use solana_sdk::{
    instruction::{AccountMeta, Instruction},
    pubkey::Pubkey,
    transaction::Transaction,
};
use std::str::FromStr;

// === Raydium AMM Swap ===
pub struct RaydiumSwap {
    pub amm_program: Pubkey,  // Raydium AMM v4
    pub amm_pool: Pubkey,
    pub amm_authority: Pubkey,
    pub user_source: Pubkey,
    pub user_destination: Pubkey,
    pub pool_source: Pubkey,
    pub pool_destination: Pubkey,
    pub serum_open_orders: Pubkey,
    pub serum_market: Pubkey,
    pub serum_program: Pubkey,
}

impl RaydiumSwap {
    pub fn new() -> Self {
        Self {
            amm_program: Pubkey::from_str("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8").unwrap(),
            amm_pool: Pubkey::default(),
            amm_authority: Pubkey::default(),
            user_source: Pubkey::default(),
            user_destination: Pubkey::default(),
            pool_source: Pubkey::default(),
            pool_destination: Pubkey::default(),
            serum_open_orders: Pubkey::default(),
            serum_market: Pubkey::default(),
            serum_program: Pubkey::from_str("9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin").unwrap(),
        }
    }

    pub fn build_swap_instruction(
        &self,
        amount_in: u64,
        minimum_amount_out: u64,
    ) -> Instruction {
        let data = raydium_amm::instruction::Swap {
            amount_in,
            minimum_amount_out,
        };
        
        Instruction {
            program_id: self.amm_program,
            accounts: vec![
                AccountMeta::new(self.amm_pool, false),
                AccountMeta::new_readonly(self.amm_authority, false),
                AccountMeta::new(self.user_source, false),
                AccountMeta::new(self.pool_source, false),
                AccountMeta::new(self.pool_destination, false),
                AccountMeta::new(self.user_destination, false),
                AccountMeta::new(self.serum_market, false),
                AccountMeta::new(self.serum_open_orders, false),
                // ... 更多必需账户
            ],
            data: data.data(),
        }
    }
}

// === Jupiter Aggregator Quote & Swap ===
pub async fn jupiter_quote(
    input_mint: &str,
    output_mint: &str,
    amount: u64,
    slippage_bps: u16,
) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
    let url = format!(
        "https://quote-api.jup.ag/v6/quote?inputMint={}&outputMint={}&amount={}&slippageBps={}",
        input_mint, output_mint, amount, slippage_bps
    );
    let response = reqwest::get(&url).await?;
    let quote = response.json::<serde_json::Value>().await?;
    Ok(quote)
}
```

---

