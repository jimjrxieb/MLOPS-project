import json
import random
from pathlib import Path

OUTPUT_FILE = Path("1-GP-GLUE/01-raw-data-lake/8b-jade/aws_saa_study_v1.jsonl")

def generate_saa_flashcards(count):
    topics = {
        "Storage": [
            ("What is Amazon EBS (Elastic Block Store)?", "High-performance block storage designed for use with Amazon EC2 for both throughput and transaction intensive workloads."),
            ("What is the difference between EBS and Instance Store?", "EBS is persistent and exists independently of an instance. Instance Store is ephemeral and data is lost when the instance is stopped or terminated."),
            ("What is Amazon EFS (Elastic File System)?", "A simple, serverless, set-and-forget elastic file system that lets you share file data without provisioning or managing storage."),
        ],
        "Serverless": [
            ("What is AWS Lambda?", "A serverless, event-driven compute service that lets you run code for virtually any type of application or backend service without provisioning or managing servers."),
            ("What is Amazon API Gateway?", "A fully managed service that makes it easy for developers to create, publish, maintain, monitor, and secure APIs at any scale."),
            ("What is AWS Step Functions?", "A low-code, visual workflow service that developers use to build distributed applications, automate IT and business processes, and build data and machine learning pipelines using AWS services."),
        ],
        "Network": [
            ("What is Amazon Route 53?", "A highly available and scalable cloud Domain Name System (DNS) web service."),
            ("What is AWS Direct Connect?", "A cloud service solution that makes it easy to establish a dedicated network connection from your premises to AWS."),
            ("What is Amazon CloudFront?", "A fast content delivery network (CDN) service that securely delivers data, videos, applications, and APIs to customers globally with low latency, high transfer speeds."),
        ]
    }
    
    flashcards = []
    topic_list = list(topics.keys())
    
    for i in range(count):
        topic = random.choice(topic_list)
        q, a = random.choice(topics[topic])
        
        flashcards.append({
            "messages": [
                {"role": "system", "content": "You are an AWS Certified Solutions Architect. Answer technical questions concisely and accurately."},
                {"role": "user", "content": f"Topic: {topic}. {q}"},
                {"role": "assistant", "content": a}
            ],
            "metadata": {"domain": "cloud", "topic": "aws-saa", "type": "study-material", "subtopic": topic}
        })
        
    return flashcards

def main():
    examples = generate_saa_flashcards(50)
    with open(OUTPUT_FILE, 'a') as f: # Append
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Appended 50 AWS SAA study pairs to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
