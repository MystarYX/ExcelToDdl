#!/usr/bin/env node

/**
 * SQL建表语句生成器测试脚本
 * 自动运行测试用例并验证结果
 */

const fs = require('fs');
const path = require('path');

// 测试用例文件路径
const TEST_CASES_FILE = path.join(__dirname, 'test-cases.json');
// API端点
const API_URL = 'http://localhost:5000/api/generate-ddl';

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m',
  gray: '\x1b[90m'
};

// 读取测试用例
function loadTestCases() {
  try {
    const data = fs.readFileSync(TEST_CASES_FILE, 'utf-8');
    return JSON.parse(data).test_cases;
  } catch (error) {
    console.error(`${colors.red}❌ 读取测试用例失败: ${error.message}${colors.reset}`);
    process.exit(1);
  }
}

// 调用API
async function callAPI(input) {
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input)
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || 'API调用失败');
    }
    return result;
  } catch (error) {
    throw new Error(`API调用异常: ${error.message}`);
  }
}

// 验证结果
function validateResult(actual, expected, testName) {
  const errors = [];

  // 提取DDL字符串
  const ddl = actual.ddl || (actual.ddls && actual.ddls[0]?.ddl);
  if (!ddl) {
    return ['❌ 未找到DDL输出'];
  }

  // 验证前缀
  if (expected.prefix && !ddl.startsWith(expected.prefix)) {
    errors.push(`前缀不匹配: 期望包含 '${expected.prefix}'`);
  }

  // 验证字段
  if (expected.fields) {
    for (const field of expected.fields) {
      if (!ddl.includes(field)) {
        errors.push(`缺少字段: ${field}`);
      }
    }
  }

  // 验证类型
  if (expected.types) {
    for (let i = 0; i < expected.types.length; i++) {
      if (!ddl.includes(expected.types[i])) {
        errors.push(`缺少类型: ${expected.types[i]}`);
      }
    }
  }

  // 验证注释
  if (expected.comments) {
    for (const comment of expected.comments) {
      // 去除注释中的引号后再验证
      const sanitizedComment = comment.replace(/[`'""]/g, '');
      const commentPattern = `COMMENT '${sanitizedComment}'`;
      if (!ddl.includes(commentPattern)) {
        errors.push(`缺少注释: ${sanitizedComment}`);
      }
    }
  }

  // 验证后缀
  if (expected.suffix) {
    const suffixParts = expected.suffix.split(' ');
    for (const part of suffixParts) {
      if (!ddl.includes(part)) {
        errors.push(`缺少后缀部分: ${part}`);
      }
    }
  }

  // 验证PRIMARY KEY
  if (expected.primaryKey) {
    if (!ddl.includes(`PRIMARY KEY (${expected.primaryKey})`)) {
      errors.push(`PRIMARY KEY不匹配: 期望 'PRIMARY KEY (${expected.primaryKey})'`);
    }
  }

  // 验证分离注释模式
  if (expected.separateComments) {
    if (!ddl.includes('COMMENT ON TABLE') || !ddl.includes('COMMENT ON COLUMN')) {
      errors.push(`缺少分离注释模式（COMMENT ON TABLE/COLUMN）`);
    }
  }

  return errors;
}

// 运行单个测试用例
async function runTestCase(testCase) {
  console.log(`\n${colors.blue}📋 测试: ${testCase.name}${colors.reset}`);
  console.log(`${colors.gray}  ${testCase.description}${colors.reset}`);

  try {
    // 调用API
    const result = await callAPI(testCase.input);

    // 验证结果
    let allPassed = true;
    const results = [];

    for (const dbType of testCase.input.databaseTypes) {
      const expected = testCase.expected[dbType];
      if (!expected) {
        console.log(`${colors.yellow}  ⚠️  跳过 ${dbType}: 缺少预期结果${colors.reset}`);
        continue;
      }

      const actual = result.ddl ? result : result.ddls.find(d => d.databaseType === dbType);
      if (!actual) {
        console.log(`${colors.red}  ❌ ${dbType}: 未找到输出${colors.reset}`);
        allPassed = false;
        continue;
      }

      const errors = validateResult(actual, expected, testCase.name);

      if (errors.length === 0) {
        console.log(`${colors.green}  ✅ ${dbType}: 通过${colors.reset}`);
        results.push({ dbType, status: 'passed' });
      } else {
        console.log(`${colors.red}  ❌ ${dbType}: 失败${colors.reset}`);
        errors.forEach(err => console.log(`${colors.red}     - ${err}${colors.reset}`));
        results.push({ dbType, status: 'failed', errors });
        allPassed = false;

        // 打印实际DDL用于调试
        console.log(`${colors.gray}  实际DDL:${colors.reset}`);
        const ddl = actual.ddl || (actual.ddls && actual.ddls[0]?.ddl);
        console.log(`${colors.gray}  ${ddl.split('\n').map(l => '    ' + l).join('\n')}${colors.reset}`);
      }
    }

    return { testCase: testCase.name, passed: allPassed, results };
  } catch (error) {
    console.log(`${colors.red}  ❌ 异常: ${error.message}${colors.reset}`);
    return { testCase: testCase.name, passed: false, error: error.message };
  }
}

// 主函数
async function main() {
  console.log(`${colors.blue}\n========================================${colors.reset}`);
  console.log(`${colors.blue}   SQL建表语句生成器 - 自动测试${colors.reset}`);
  console.log(`${colors.blue}========================================${colors.reset}`);

  // 检查服务是否运行
  console.log(`\n${colors.gray}检查服务状态...${colors.reset}`);
  try {
    const response = await fetch('http://localhost:5000');
    if (!response.ok) throw new Error('服务未响应');
    console.log(`${colors.green}✓ 服务运行正常${colors.reset}\n`);
  } catch (error) {
    console.error(`${colors.red}❌ 服务未运行，请先启动: coze dev${colors.reset}`);
    process.exit(1);
  }

  // 加载测试用例
  const testCases = loadTestCases();
  console.log(`${colors.blue}共 ${testCases.length} 个测试用例${colors.reset}\n`);

  // 运行测试
  const results = [];
  for (let i = 0; i < testCases.length; i++) {
    const result = await runTestCase(testCases[i]);
    results.push(result);
  }

  // 汇总结果
  console.log(`\n${colors.blue}========================================${colors.reset}`);
  console.log(`${colors.blue}   测试结果汇总${colors.reset}`);
  console.log(`${colors.blue}========================================${colors.reset}`);

  const passed = results.filter(r => r.passed).length;
  const failed = results.length - passed;

  console.log(`\n总计: ${results.length} 个测试用例`);
  console.log(`${colors.green}✓ 通过: ${passed}${colors.reset}`);
  if (failed > 0) {
    console.log(`${colors.red}✗ 失败: ${failed}${colors.reset}`);
  }

  console.log(`\n详细信息:`);
  results.forEach(r => {
    const icon = r.passed ? `${colors.green}✓${colors.reset}` : `${colors.red}✗${colors.reset}`;
    console.log(`  ${icon} ${r.testCase}`);
  });

  console.log(`\n${colors.blue}========================================${colors.reset}\n`);

  // 退出码
  process.exit(failed > 0 ? 1 : 0);
}

// 运行
main().catch(error => {
  console.error(`${colors.red}❌ 脚本执行失败: ${error.message}${colors.reset}`);
  process.exit(1);
});
