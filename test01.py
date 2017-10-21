import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin


class Blockchain(object):
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # Эхлэлийн блок үүсгэнэ
        self.new_block(previous_hash=1, proof=100)

    def register_node(self, address):
        """
        Shine node-g Blockchain-nii node-uud dund nemeh

        :param address: <str> Node-n hayg. 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        Ugugdsun blockchain n huchintei baigaag togtooh

        :param chain: <list> A blockchain
        :return: <bool> Huchintei bol True, Ugu bol False
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n----Google-------\n")
            # Тухайн блок нь Хэш утга зөв байгаа эсэхийг шалгах
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Proof of work зөв байгаа эсэхийг шалгах
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        Энэ нь зөвшилцлийн алгоритм, Энэ нь сүлжээн дэр хамгийн урт chain-г сольж зөрчилдөөнийг шийдвэрлэдэг.

        :return: <bool> Chain солигдсон бол True, Үгүй бол False
        """

        neighbours = self.nodes
        new_chain = None

        # Хамгийн урт chain-g хайж байгаа
        max_length = len(self.chain)

        # Сүлжээнд байгаа бүх node-ooс chain-g шалгаж, баталгаажуулна.
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Илүү урт , гинж хүчинтэй эсэхийг шалгах
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Хэрэв урт, хүчинтэй бол блок, гинжээ шинэчлэх
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash=None):
        """
        Blockchain-нд шинэ блок үүсгэх
        :param proof: <int> Proof of Work алгоритмоор өгсөн шинэ ажил/Proof/
        :param previous_hash: (Optional) <str> Өмнөх блокын хэш
        :return: <dict> Шинэ Блок
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Одооны гүйлгээний list-г цэвэрлэх
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        Шинэ гүйлгээг нээж дараагийн mine- хийгдэх блок руу оруулах

        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Block-ийн SHA-256 хэш утгийг гаргаж авах
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        """
        Энгийн Proof of Work алгоритм:
         - p нь өмнөх p' байх хэш нь 0000-ээр эхлэдэг p' тоог олох ажил
         - p' нь шинэ proof, p нь өмнөх proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Proof-ийг нотлох
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
@cross_origin()
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    block = blockchain.new_block(proof)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

# @app.route('/nodes/register', methods=['POST'])
# def register_nodes():
#     values = request.get_json()
#
#     nodes = values.get('nodes')
#     if nodes is None:
#         return "Error: Please supply a valid list of nodes", 400
#
#     for node in nodes:
#         blockchain.register_node(node)
#
#     response = {
#         'message': 'New nodes have been added',
#         'total_nodes': list(blockchain.nodes),
#     }
#     return jsonify(response), 201
#
# # @app.route('/',methods=['GET'])
# # def gogle():
# #
# #     response = {
# #         'chain': blockchain.chain,
# #         'length': len(blockchain.chain),
# #
# #     }
# #     return jsonify(response), 200
#
# @app.route('/nodes/resolve', methods=['GET'])
# def consensus():
#     replaced = blockchain.resolve_conflicts()
#
#     if replaced:
#         response = {
#             'message': 'Our chain was replaced',
#             'new_chain': blockchain.chain
#         }
#     else:
#         response = {
#             'message': 'Our chain is authoritative',
#             'chain': blockchain.chain
#         }
#
#     return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)