/* eslint-disable no-await-in-loop */
const DigiByte = require('digibyte');
const { default: axios } = require('axios');
const { getRequestHeaders } = require('../helpers/get-request-headers');
const { getApiKey } = require('../helpers/get-api-key');

class DigiByteService {
  UTXO_ENDPOINT = 'https://dgb.nownodes.io/api/v2/utxo';

  ADDRESS_ENDPOINT = 'https://dgb.nownodes.io/api/v2/address';

  JSON_RPC_ENDPOINT = 'https://dgb.nownodes.io';

  TRANSACTION_ENDPOINT = 'https://dgb.nownodes.io/api/v2/tx';

  SAT_IN_DGB = 100000000;

  FEE_TO_SEND_DGB = 0.0000553 * this.SAT_IN_DGB;

  MINER_FEE = 100000;

  TRANSACTIONS_RECEIVE_INTERVAL = 20;

  TRANSACTIONS_RECEIVE_TIMEOUT = 1000;

  static getNewWallet() {
    const wallet = DigiByte.PrivateKey();
    return {
      address: wallet.toLegacyAddress().toString(),
      privateKey: wallet.toWIF(),
    };
  }

  async getUtxos(address) {
    const utxoResponse = await axios.get(
      `${this.UTXO_ENDPOINT}/${address}?confirmed=true`,
      getRequestHeaders(),
    );
    const { data: utxos } = await utxoResponse;
    return utxos;
  }
  async getWalletBalance(address) {
    const balanceResponse = await axios.get(
      `${this.ADDRESS_ENDPOINT}/${address}`,
      getRequestHeaders(),
    );
    const { data: balanceData } = await balanceResponse;
    const balanceInSatoshi = balanceData?.balance;
    return balanceInSatoshi ? (balanceInSatoshi / this.SAT_IN_DGB) : 0;
  }

async createTransaction(privateKey, origin, destination, amount) {
    const pk = new DigiByte.PrivateKey(privateKey);
    let utxos = await this.getUtxos(origin);
    let transactionAmount = amount

      transactionAmount = +(manualAmount * this.SAT_IN_DGB);

    utxos = utxos.map((utxo) => ({
      txId: utxo.txid,
      vout: +utxo.vout,
      address: origin,
      scriptPubKey: DigiByte.Script.fromAddress(origin),
      amount: parseFloat(utxo.value) / this.SAT_IN_DGB,
    }));

    if (!transactionAmount) {
      throw new Error('Not enough balance');
    }
    transactionAmount = transactionAmount.toFixed(5);
    transactionAmount = +transactionAmount;

    // if there's no manual amount we're passing all utxos, so we subtract the fee ourselves
    if (!manualAmount) {
      transactionAmount -= this.FEE_TO_SEND_DGB;
    }

    return new DigiByte.Transaction()
      .from(utxos)
      .to(destination, transactionAmount)
      .fee(this.MINER_FEE)
      .change(origin)
      .sign(pk);
  }


  async sendTransaction(address, my_address, privateKey, amount) {
    const to = address
    const from = my_address
    const transaction = await this.createTransaction(privateKey, from, to, amount);
    const serializedTransaction = transaction.serialize(true);
    const transactionResult = await this.sendRawTx(serializedTransaction);
    return transactionResult;
  }

  async sendRawTx(serializedTransaction) {
    const payload = {
      API_key: 'ae5edad6-01b8-44ef-9586-8c65976212f5',
      jsonrpc: '2.0',
      id: 'test',
      method: 'sendrawtransaction',
      params: [
        serializedTransaction,
      ],
    };
    const response = await axios.post(this.JSON_RPC_ENDPOINT, payload);
    const resultData = await response.data;
    return resultData;
  }

  async getIncommingTransactions(address, itemsCount = 50) {
    // eslint-disable-next-line no-promise-executor-return
    const snooze = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const response = await axios.get(
      `${this.ADDRESS_ENDPOINT}/${address}`,
      getRequestHeaders(),
    );

    const { data: addressResult } = await response;
    const { txids: transactionIds } = addressResult;

    if (!transactionIds) {
      return [];
    }

    const lastTransactionIds = transactionIds.slice(0, itemsCount);
    const transactionResult = [];
    const transactionsObservables = lastTransactionIds.map((transactionId) => axios.get(`${this.TRANSACTION_ENDPOINT}/${transactionId}`, getRequestHeaders()));

    for (let i = 0; i < transactionsObservables.length; i += 1) {
      if (i % this.TRANSACTIONS_RECEIVE_INTERVAL === 0) {
        await snooze(this.TRANSACTIONS_RECEIVE_TIMEOUT);
      }
      const transactionResulItem = await transactionsObservables[i];
      transactionResult.push(transactionResulItem);
    }

    const transactionResultData = await Promise.all(
      transactionResult.map((t) => t.data),
    );

    const result = transactionResultData.filter((transaction) => {
      const vin = transaction.vin.find(
        (vInItem) => vInItem.addresses.some((inAddress) => inAddress === address),
      );
      return !vin;
    });
    return result;
  }
}

module.exports = { DigiByteService };
