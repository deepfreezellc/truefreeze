from brownie import accounts, exceptions, chain
from scripts.deploy_functions import deploy_contracts, deployAndSetAdmin
from scripts.utils import calculateWithdrawCost

from web3 import Web3
import pytest


def sendEth(alice):
    accounts[2].transfer(alice, Web3.toWei(9.5, "Ether"))
    accounts[3].transfer(alice, Web3.toWei(9.5, "Ether"))


# Test locking and minting of frETH and NFT
@pytest.mark.parametrize("amountToLock", [1, 4, 5])
@pytest.mark.parametrize("timeToLock", [30, 89, 365, 730, 1095])
def test_deposit(admin, alice, amountToLock, timeToLock):
    weth, freth, nft, frz, deepfreeze = deployAndSetAdmin(admin)
    amountToLock = Web3.toWei(amountToLock, "Ether")
    weth.deposit({"from": alice, "value": amountToLock})
    weth.approve(deepfreeze.address, amountToLock, {"from": alice})
    deepfreeze.lockWETH(amountToLock, timeToLock, {"from": alice})
    theoric_frEth = (timeToLock * amountToLock) / 365
    print(
        f"Delta between theoric and from contract is {abs(freth.balanceOf(alice) - theoric_frEth.as_integer_ratio()[0])} Gwei"
    )
    assert abs(freth.balanceOf(alice) - theoric_frEth.as_integer_ratio()[0]) < 200
    assert freth.totalSupply() == freth.balanceOf(alice)
    assert nft.balanceOf(alice) == 1
    assert nft.ownerOf(1) == alice
    assert weth.balanceOf(deepfreeze.address) == amountToLock


# Test position is correct
@pytest.mark.parametrize("amountToLock", [1, 4, 5])
@pytest.mark.parametrize("timeToLock", [30, 89, 409, 201])
def test_positionCorrect(admin, alice, amountToLock, timeToLock):
    weth, freth, nft, frz, deepfreeze = deployAndSetAdmin(admin)
    amountToLock = Web3.toWei(amountToLock, "Ether")
    weth.deposit({"from": alice, "value": amountToLock})
    weth.approve(deepfreeze.address, amountToLock, {"from": alice})
    deepfreeze.lockWETH(amountToLock, timeToLock, {"from": alice})
    theoric_frEth = timeToLock * amountToLock / 365
    (
        amountLocked,
        tokenMinted,
        timestampLock,
        timestampUnlock,
        isActive,
    ) = deepfreeze.getPositions(1)
    print(
        f"Delta between theoric and tokenMinted is {abs(freth.balanceOf(alice) - theoric_frEth.as_integer_ratio()[0])} Gwei"
    )
    assert amountLocked == amountToLock
    assert tokenMinted == freth.balanceOf(alice)
    assert abs(tokenMinted - theoric_frEth.as_integer_ratio()[0]) < 200
    assert (timestampUnlock - timestampLock) / (3600 * 24) == timeToLock
    assert isActive == True


# Test progress computation
def test_calculateProgress(admin, alice):
    weth, freth, nft, frz, deepfreeze = deployAndSetAdmin(admin)
    amountToLock = Web3.toWei(1, "Ether")
    weth.deposit({"from": alice, "value": amountToLock})
    weth.approve(deepfreeze.address, amountToLock, {"from": alice})
    deepfreeze.lockWETH(amountToLock, 500, {"from": alice})
    assert deepfreeze.getProgress(1) == 0
    chain.sleep(3600 * 24 * 125)
    chain.mine()
    assert deepfreeze.getProgress(1) == 25
    chain.sleep(3600 * 24 * 125)
    chain.mine()
    assert deepfreeze.getProgress(1) == 50
    chain.sleep(3600 * 24 * 125)
    chain.mine()
    assert deepfreeze.getProgress(1) == 75
    chain.sleep(3600 * 24 * 125)
    chain.mine()
    assert deepfreeze.getProgress(1) == 100


# Test unlocking cost
@pytest.mark.parametrize("amountToLock", [0.5, 0.03, 0.00001])
@pytest.mark.parametrize("timeToLock", [30, 89, 409, 201])
def test_unlockingCost(admin, alice, amountToLock, timeToLock):
    weth, freth, nft, frz, deepfreeze = deployAndSetAdmin(admin)
    amountToLock = Web3.toWei(amountToLock, "Ether")
    weth.deposit({"from": alice, "value": amountToLock})
    weth.approve(deepfreeze.address, amountToLock, {"from": alice})
    deepfreeze.lockWETH(amountToLock, timeToLock, {"from": alice})
    progress = deepfreeze.getProgress(1)
    (
        amountLocked,
        tokenMinted,
        timestampLock,
        timestampUnlock,
        isActive,
    ) = deepfreeze.getPositions(1)
    delta = abs(
        calculateWithdrawCost(progress, tokenMinted) - deepfreeze.getUnlockCost(1)
    )
    print(f"Delta at {progress} % between theoric and from contract {delta} Gwei")
    assert delta <= 200
    chain.sleep(3600 * 24 * round((timeToLock / 4)))
    chain.mine()
    progress = deepfreeze.getProgress(1)
    delta = abs(
        calculateWithdrawCost(progress, tokenMinted) - deepfreeze.getUnlockCost(1)
    )
    print(f"Delta at {progress} % between theoric and from contract {delta} Gwei")
    assert delta <= 200

    chain.sleep(3600 * 24 * round((timeToLock / 2)))
    chain.mine()
    progress = deepfreeze.getProgress(1)
    delta = abs(
        calculateWithdrawCost(progress, tokenMinted) - deepfreeze.getUnlockCost(1)
    )
    print(f"Delta at {progress} % between theoric and from contract {delta} Gwei")
    assert delta <= 200

    chain.sleep(3600 * 24 * round((timeToLock / 2)))
    chain.mine()
    progress = deepfreeze.getProgress(1)
    delta = abs(
        calculateWithdrawCost(progress, tokenMinted) - deepfreeze.getUnlockCost(1)
    )
    print(f"Delta at {progress} % between theoric and from contract {delta} Gwei")
    assert delta <= 200


# Test WethFees
@pytest.mark.parametrize("amountToLock", [0.5, 0.03, 0.00001])
def test_WETHfees(admin, alice, amountToLock):
    weth, freth, nft, frz, deepfreeze = deployAndSetAdmin(admin)
    amountToLock = Web3.toWei(amountToLock, "Ether")
    weth.deposit({"from": alice, "value": amountToLock})
    weth.approve(deepfreeze.address, amountToLock, {"from": alice})
    deepfreeze.lockWETH(amountToLock, 400, {"from": alice})
    assert deepfreeze.getWethFees(1) == (amountToLock * 0.0025).as_integer_ratio()[0]
    chain.sleep(3600 * 24 * 200)
    chain.mine()
    assert deepfreeze.getWethFees(1) == (amountToLock * 0.0025).as_integer_ratio()[0]
    chain.sleep(3600 * 24 * 200)
    chain.mine()
    assert deepfreeze.getWethFees(1) == 0